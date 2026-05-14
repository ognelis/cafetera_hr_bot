"""Evaluate the RAG pipeline using RAGAS ``@experiment`` + ``aevaluate()``.

Two-phase evaluation:

1. **QA phase** — ``@experiment``-decorated function runs each testset question
   through the QAService, collecting answer + retrieved contexts.  The
   experiment framework handles naming, parameterization (via
   ``system_prompt`` kwarg), and JSONL persistence.

2. **Scoring phase** — ``aevaluate()`` scores the collected results with
   RAGAS metrics (Faithfulness, ContextPrecisionWithoutReference,
   AnswerRelevancy, ContextRecall).  This eliminates manual per-metric
   scoring loops and error handling — ``aevaluate()`` manages all of that
   internally.

Usage:
    uv run python ragas/evaluate.py
    uv run python ragas/evaluate.py --testset ragas/testset.json
    uv run python ragas/evaluate.py --name my_experiment
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _common import (
    DEFAULT_TESTSET,
    EVAL_SYSTEM_PROMPT,
    EVALUATOR_MAX_TOKENS,
    MAX_CONCURRENT_QA,
    build_eval_metrics,
    build_ragas_embeddings,
    build_ragas_llm,
    build_ragas_resources,
    load_testset,
    print_summary,
    score_with_metrics,
)
from openai import AsyncOpenAI
from ragas import Dataset, EvaluationDataset, experiment
from ragas.backends import LocalJSONLBackend

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.resources import build_qa_service, close_rag_resources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_EXPERIMENTS_DIR = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Experiment name builder
# ---------------------------------------------------------------------------

def _build_experiment_name(
    settings: RagServiceSettings,
    *,
    override: str | None = None,
) -> str:
    """Construct a meaningful experiment name from settings."""
    if override:
        return override

    model_slug = settings.llm_model.replace(":", "_").replace("/", "_")
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M")
    reranker_tag = "rerank" if settings.reranking_enabled else "norank"
    return f"eval_{model_slug}_{reranker_tag}_{ts}"


# ---------------------------------------------------------------------------
# Main evaluation entry point
# ---------------------------------------------------------------------------

async def run_evaluation(
    testset_path: Path,
    *,
    name_override: str | None = None,
) -> None:
    """Run two-phase RAGAS evaluation.

    Phase 1 (QA): ``@experiment``-decorated function runs each testset row
    through the QAService, collecting answer + retrieved contexts.  The
    experiment framework handles naming, parameterization, and JSONL storage.

    Phase 2 (Scoring): ``aevaluate()`` scores the collected results with
    pre-configured RAGAS metrics.  It manages metric execution, progress
    tracking, and error recovery internally.
    """
    settings = RagServiceSettings()

    # 1. Load testset.
    samples = load_testset(testset_path)
    logger.info("Loaded %d samples from %s", len(samples), testset_path)

    has_reference_contexts = all(
        s.get("reference_contexts") for s in samples
    )
    has_reference = all(
        s.get("reference") for s in samples
    )

    # 2. Build scorer LLM + embeddings (used in Phase 2).
    #    Single evaluator LLM with the Faithfulness budget (16384) since
    #    aevaluate() uses it for all metrics.
    client_cache: dict[tuple[str, str], AsyncOpenAI] = {}
    ragas_llm = build_ragas_llm(
        settings, client_cache, max_tokens=EVALUATOR_MAX_TOKENS,
    )
    ragas_embeddings = build_ragas_embeddings(
        settings, client_cache, interface="legacy",
    )

    # Pre-configure metrics — ``aevaluate()`` won't override llm/embeddings
    # that are already set on each metric.  Composition (including conditional
    # zero-LLM metrics) is owned by ``build_eval_metrics()`` in ``_common.py``
    # and shared with ``optimize_prompt.py``.
    metrics: list[Any] = build_eval_metrics(
        ragas_llm,
        ragas_embeddings,
        has_reference_contexts=has_reference_contexts,
        has_reference=has_reference,
    )

    # 3. Phase 1 — QA via @experiment.
    res = await build_ragas_resources(settings)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_QA)
    qa_cache: dict[str, Any] = {}

    try:

        @experiment()
        async def rag_eval(
            row: dict[str, Any],
            *,
            system_prompt: str = EVAL_SYSTEM_PROMPT,
        ) -> dict[str, Any]:
            """Ask a single testset question and return answer + contexts.

            Parameters
            ----------
            row : dict
                A testset sample with keys like ``user_input``, ``reference``, etc.
            system_prompt : str
                System prompt for the QA service.  Passed through from
                ``arun(system_prompt=...)`` to support parameterization sweeps.
            """
            async with semaphore:
                question = row.get("user_input", "")
                if not question:
                    logger.warning("Sample has no user_input, skipping")
                    return {**row, "response": "", "retrieved_contexts": []}

                # Lazily build QA service per unique system_prompt.
                if system_prompt not in qa_cache:
                    qa_cache[system_prompt] = build_qa_service(
                        res, system_prompt, include_metadata=True,
                    )
                qa = qa_cache[system_prompt]

                logger.info("Asking: %s", question[:80])
                try:
                    answer, contexts = await qa.ask_with_contexts(question)
                except Exception:
                    logger.exception("Failed on question: %s", question[:80])
                    answer, contexts = "", []

                return {
                    **row,
                    "response": answer,
                    "retrieved_contexts": contexts,
                }

        dataset: Dataset = Dataset("ragas_eval", "inmemory", data=samples)
        exp_name = _build_experiment_name(settings, override=name_override)
        backend = LocalJSONLBackend(root_dir=str(_EXPERIMENTS_DIR))

        experiment_result = await rag_eval.arun(
            dataset, name=exp_name, backend=backend,
        )

    finally:
        await close_rag_resources(res)

    # 4. Collect QA results for scoring.
    collected = [item for item in experiment_result if isinstance(item, dict)]
    if not collected:
        logger.error("No results collected. Check RAG service and Qdrant.")
        sys.exit(1)

    logger.info(
        "Phase 1 complete: %d samples answered. Starting scoring.",
        len(collected),
    )

    # 5. Phase 2 — Score with ``aevaluate()`` (via shared helper).
    eval_dataset = EvaluationDataset.from_list(collected)

    result = await score_with_metrics(
        eval_dataset, metrics, experiment_name=exp_name,
    )

    # aevaluate returns EvaluationResult when return_executor=False (default).
    from ragas.evaluation import EvaluationResult as EvalResult
    assert isinstance(result, EvalResult)

    # 6. Print and save results.
    print(result)
    print_summary(result)

    output_path = testset_path.parent / "scores.json"
    # Replace NaN/Infinity with None so the output is strict-JSON compliant
    # (default json.dumps emits non-standard NaN tokens rejected by JSON.parse/jq).
    sanitized_scores = _sanitize_for_json(result.scores)
    output_path.write_text(
        json.dumps(sanitized_scores, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    logger.info("Scores saved to %s", output_path)
    logger.info(
        "Experiment '%s' saved to %s/experiments/", exp_name, _EXPERIMENTS_DIR,
    )


def _sanitize_for_json(value: Any) -> Any:
    """Recursively replace NaN/Infinity floats with None for strict JSON output."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_for_json(v) for v in value)
    return value


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate RAG pipeline with RAGAS metrics",
    )
    parser.add_argument(
        "--testset",
        type=Path,
        default=DEFAULT_TESTSET,
        help=f"Path to testset JSON (default: {DEFAULT_TESTSET})",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Override experiment name (default: auto-generated from settings)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(run_evaluation(args.testset, name_override=args.name))
