"""Evaluate the RAG pipeline using RAGAS metrics.

Loads a testset from ragas/testset.json, runs each question through the
QAService (with contexts), and scores using RAGAS collections metrics:
Faithfulness, ContextPrecisionWithoutReference, AnswerRelevancy.

ContextRecall is included only when testset samples contain a 'reference' field.

Usage:
    uv run python ragas/evaluate.py
    uv run python ragas/evaluate.py --testset ragas/testset.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecisionWithoutReference,
    ContextRecall,
    Faithfulness,
)

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.rag.chain import build_llm
from cafetera_rag_service.rag.retriever import (
    build_embeddings,
    build_qdrant_client,
    build_sparse_embeddings,
)
from cafetera_rag_service.resources import (
    RagResources,
    build_qa_service,
    build_reranker,
    close_rag_resources,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_TESTSET = Path(__file__).parent / "testset.json"


async def build_ragas_resources(settings: RagServiceSettings) -> RagResources:
    """Lightweight resource init for RAGAS evaluation.

    Initializes only what the QAService needs (Qdrant, embeddings, LLM,
    sparse embeddings, reranker).  Skips S3 — RAGAS doesn't ingest documents.

    On any failure, already-initialized resources are closed before re-raising
    so we do not leak sockets or file descriptors.
    """
    res = RagResources(settings=settings)
    try:
        # 1. Qdrant + embeddings
        res.qdrant_client = build_qdrant_client(settings)
        res.embeddings = build_embeddings(settings)

        # 2. Sparse embeddings (optional)
        res.sparse_embeddings = build_sparse_embeddings(settings)

        # 3. Reranker (optional) — returns (None, None) when disabled.
        reranker, reranker_http = build_reranker(settings)
        res.reranker = reranker
        res.reranker_http_client = reranker_http

        # 4. LLM
        res.llm = build_llm(settings)
    except Exception:
        logger.exception("Failed to initialize RAGAS resources; cleaning up")
        await close_rag_resources(res)
        raise

    return res

# Default system prompt for evaluation — matches the admin global prompt.
_EVAL_SYSTEM_PROMPT = """\
Ты — ассистент компании. Отвечай на вопросы сотрудников
строго на основе предоставленного контекста.
Не используй информацию из общих знаний, даже если она кажется очевидной.

Правила:
1. Опирайся строго на предоставленный контекст — не выдумывай
   и не дополняй из общих знаний.
2. Если в контексте недостаточно информации — скажи:
   «В доступных документах нет ответа на этот вопрос».
3. Если документы противоречат друг другу — укажи оба варианта
   и отдавай предпочтение более актуальному.
4. Отвечай на русском языке, по существу, деловым и понятным тоном.
5. При использовании информации из документа — указывай его название.
6. Используй нумерованные списки для пошаговых инструкций,
   буллиты — для перечислений из 3+ пунктов.

### Контекст:
{context}"""


def _load_testset(path: Path) -> list[dict[str, Any]]:
    """Load testset JSON and return list of sample dicts."""
    if not path.exists():
        logger.error("Testset not found at %s. Run generate_testset.py first.", path)
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        logger.error("Testset at %s is empty or not a list.", path)
        sys.exit(1)

    return data


# -- LLM tuning for local models -------------------------------------------------
# Small local models (e.g. Qwen3.5-4B q4) are prone to repetition loops during
# NER extraction in Faithfulness scoring — the model gets stuck repeating tokens
# until max_tokens is exhausted, producing invalid JSON.  Faithfulness therefore
# needs a generous ceiling; the other metrics only emit short JSON verdicts.
#
# Per-metric ceilings matter for servers that pre-allocate KV-cache per request
# (llama.cpp with `n_predict`, Ollama with `num_predict`).  A lower ceiling for
# short-output metrics frees VRAM/RAM during their runs.
#
# NOTE: The per-request output budget must not exceed the per-slot context
# capacity.  For llama.cpp with `--parallel N` and `--ctx-size C`, each slot
# holds C/N tokens (prompt + output combined).  `ragas/run.sh` forces
# LLM_PARALLEL=1 so the full LLM_NUM_CTX is available per request; the values
# below leave generous headroom (prompt ~4–8k + output).
_FAITHFULNESS_MAX_TOKENS = 16384  # NER extraction: long JSON output
_SHORT_OUTPUT_MAX_TOKENS = 4096   # verdicts / question variants / binary class


def _resolve_llm_endpoint(
    settings: RagServiceSettings,
) -> tuple[str, str, str]:
    """Return (base_url, api_key, provider) for the LLM endpoint."""
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return settings.llm_base_url, settings.llm_api_key, provider
    if provider == "llamacpp":
        return f"{settings.llm_base_url}/v1", "no-key", provider
    return f"{settings.llm_base_url}/v1", "ollama", provider  # ollama default


def _resolve_embedding_endpoint(
    settings: RagServiceSettings,
) -> tuple[str, str]:
    """Return (base_url, api_key) for the embedding endpoint."""
    provider = settings.embedding_provider.lower()
    if provider == "openai":
        return settings.embedding_base_url, settings.embedding_api_key
    if provider == "llamacpp":
        return settings.embedding_base_url, "no-key"
    return f"{settings.embedding_base_url}/v1", "ollama"  # ollama default


def _get_async_client(
    base_url: str,
    api_key: str,
    cache: dict[tuple[str, str], AsyncOpenAI],
) -> AsyncOpenAI:
    """Return a cached AsyncOpenAI client keyed by (base_url, api_key).

    Shares a single connection pool across LLM + embeddings when they target
    the same endpoint (common for local Ollama/llama.cpp deployments).
    """
    key = (base_url, api_key)
    if key not in cache:
        cache[key] = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return cache[key]


def _build_ragas_llm(
    settings: RagServiceSettings,
    client_cache: dict[tuple[str, str], AsyncOpenAI],
    *,
    max_tokens: int,
):
    """Build a RAGAS evaluator LLM from configured provider.

    The ``max_tokens`` budget drives both the OpenAI-compat ``max_tokens`` field
    and the backend-specific generation cap (Ollama ``num_predict`` /
    llama.cpp ``n_predict``) so that servers which pre-allocate KV-cache per
    request size their slots to the metric's actual needs.
    """
    base_url, api_key, provider = _resolve_llm_endpoint(settings)
    async_client = _get_async_client(base_url, api_key, client_cache)

    ragas_llm = llm_factory(
        model=settings.llm_model,
        provider="openai",
        client=async_client,
    )

    # Inject extra_body into the instructor client's default kwargs so that
    # every chat.completions.create() call includes the context window hint
    # and generation cap.
    # RAGAS's InstructorLLM stores extra_body in model_args but the instructor
    # layer may not forward it reliably; setting it on client.kwargs uses
    # instructor's own handle_kwargs() merge which is guaranteed to apply.
    extra_body: dict[str, Any] = {}
    if provider == "ollama":
        options: dict[str, Any] = {}
        if settings.llm_num_ctx:
            options["num_ctx"] = settings.llm_num_ctx
        # num_predict: Ollama's per-request generation cap.
        options["num_predict"] = max_tokens
        extra_body = {"options": options}
    elif provider == "llamacpp":
        if settings.llm_num_ctx:
            extra_body["n_ctx"] = settings.llm_num_ctx
        # n_predict: llama.cpp's per-request generation cap (default 2048-4096).
        extra_body["n_predict"] = max_tokens

    ragas_llm.client.kwargs["max_tokens"] = max_tokens
    if extra_body:
        ragas_llm.client.kwargs["extra_body"] = extra_body

    return ragas_llm


def _build_ragas_embeddings(
    settings: RagServiceSettings,
    client_cache: dict[tuple[str, str], AsyncOpenAI],
):
    """Build RAGAS embeddings from configured provider."""
    base_url, api_key = _resolve_embedding_endpoint(settings)
    async_client = _get_async_client(base_url, api_key, client_cache)
    return embedding_factory(
        provider="openai",
        model=settings.embedding_model,
        client=async_client,
        interface="modern",
    )


def _build_scorers(
    settings: RagServiceSettings,
    client_cache: dict[tuple[str, str], AsyncOpenAI],
    ragas_embeddings: Any,
    *,
    has_reference: bool,
) -> dict[str, Any]:
    """Construct RAGAS metric scorers once; reused across all samples.

    Faithfulness gets a heavy-budget LLM wrapper (long NER JSON output);
    the other metrics share a light-budget wrapper.  Both wrappers reuse the
    same underlying AsyncOpenAI connection pool via ``client_cache`` — only
    the instructor-layer ``max_tokens`` differs.
    """
    llm_heavy = _build_ragas_llm(
        settings, client_cache, max_tokens=_FAITHFULNESS_MAX_TOKENS,
    )
    llm_light = _build_ragas_llm(
        settings, client_cache, max_tokens=_SHORT_OUTPUT_MAX_TOKENS,
    )

    scorers: dict[str, Any] = {
        "faithfulness": Faithfulness(llm=llm_heavy),
        "context_precision": ContextPrecisionWithoutReference(llm=llm_light),
        "answer_relevancy": AnswerRelevancy(
            llm=llm_light, embeddings=ragas_embeddings,
        ),
    }
    if has_reference:
        scorers["context_recall"] = ContextRecall(llm=llm_light)
    return scorers


async def _score_one(
    scorers: dict[str, Any],
    *,
    question: str,
    answer: str,
    contexts: list[str],
    reference: str | None,
    index: int,
) -> dict[str, Any]:
    """Score a single sample with all configured metrics.

    Runs sequentially to avoid piling up multiple full-context prompts in
    RAM for the same sample simultaneously.
    """
    row: dict[str, Any] = {"user_input": question}

    try:
        result = await scorers["faithfulness"].ascore(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
        )
        row["faithfulness"] = result.value
    except Exception:
        logger.exception("Faithfulness failed for sample %d", index)
        row["faithfulness"] = None

    try:
        result = await scorers["context_precision"].ascore(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
        )
        row["context_precision"] = result.value
    except Exception:
        logger.exception("ContextPrecision failed for sample %d", index)
        row["context_precision"] = None

    try:
        result = await scorers["answer_relevancy"].ascore(
            user_input=question,
            response=answer,
        )
        row["answer_relevancy"] = result.value
    except Exception:
        logger.exception("AnswerRelevancy failed for sample %d", index)
        row["answer_relevancy"] = None

    if "context_recall" in scorers and reference is not None:
        try:
            result = await scorers["context_recall"].ascore(
                user_input=question,
                retrieved_contexts=contexts,
                reference=reference,
            )
            row["context_recall"] = result.value
        except Exception:
            logger.exception("ContextRecall failed for sample %d", index)
            row["context_recall"] = None

    return row


def _print_summary(scores: list[dict[str, Any]]) -> None:
    """Print aggregate summary table."""
    metric_names = [
        k for k in scores[0] if k != "user_input" and k != "response"
    ]

    print("\n" + "=" * 60)
    print("RAGAS Evaluation Summary")
    print("=" * 60)

    for metric in metric_names:
        values = [s[metric] for s in scores if s.get(metric) is not None]
        if values:
            avg = sum(values) / len(values)
            min_v = min(values)
            max_v = max(values)
            print(
                f"  {metric:<30s}  "
                f"avg={avg:.3f}  min={min_v:.3f}  max={max_v:.3f}  "
                f"n={len(values)}/{len(scores)}"
            )
        else:
            print(f"  {metric:<30s}  NO VALID SCORES")

    print("=" * 60)


async def evaluate(testset_path: Path) -> None:
    """Pipelined evaluation: ask → score → discard, per sample.

    Memory-friendly variant of the prior two-phase flow: we no longer hold
    every answer + retrieved_contexts in RAM while scoring.  Each sample's
    large strings go out of scope right after scoring, freeing RAM for the
    next iteration.  Scores are checkpointed to disk after each sample so a
    crash mid-run doesn't waste prior work.
    """
    settings = RagServiceSettings()

    # 1. Load testset.
    samples = _load_testset(testset_path)
    logger.info("Loaded %d samples from %s", len(samples), testset_path)

    has_reference = all(
        "reference" in s and s["reference"] for s in samples
    )

    # 2. Build RAGAS scorers once (shared AsyncOpenAI client per endpoint,
    #    per-metric max_tokens budgets).
    client_cache: dict[tuple[str, str], AsyncOpenAI] = {}
    ragas_embeddings = _build_ragas_embeddings(settings, client_cache)
    scorers = _build_scorers(
        settings,
        client_cache,
        ragas_embeddings,
        has_reference=has_reference,
    )

    # 3. Build QA stack and run the pipelined loop.
    output_path = testset_path.parent / "scores.json"
    scores: list[dict[str, Any]] = []
    res = await build_ragas_resources(settings)
    try:
        qa = build_qa_service(res, _EVAL_SYSTEM_PROMPT, include_metadata=True)

        for i, sample in enumerate(samples):
            question = sample.get("user_input", "")
            if not question:
                logger.warning("Sample %d has no user_input, skipping", i)
                continue

            logger.info(
                "[%d/%d] Asking: %s", i + 1, len(samples), question[:80],
            )
            try:
                answer, contexts = await qa.ask_with_contexts(question)
            except Exception:
                logger.exception("Failed on sample %d", i)
                answer, contexts = "", []

            row = await _score_one(
                scorers,
                question=question,
                answer=answer,
                contexts=contexts,
                reference=sample.get("reference") if has_reference else None,
                index=i,
            )
            scores.append(row)
            logger.info(
                "[%d/%d] %s",
                i + 1,
                len(samples),
                {
                    k: f"{v:.3f}" if isinstance(v, float) else v
                    for k, v in row.items()
                },
            )

            # Checkpoint after every sample so a crash mid-run isn't wasted.
            output_path.write_text(
                json.dumps(scores, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            # answer/contexts go out of scope here → GC reclaims their RAM
            # before the next iteration allocates new context strings.
    finally:
        await close_rag_resources(res)

    if not scores:
        logger.error("No results collected. Check RAG service and Qdrant.")
        sys.exit(1)

    _print_summary(scores)
    logger.info("Detailed scores saved to %s", output_path)


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
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(evaluate(args.testset))
