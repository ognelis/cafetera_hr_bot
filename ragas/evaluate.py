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
from cafetera_rag_service.resources import (
    build_qa_service,
    build_rag_resources,
    close_rag_resources,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_TESTSET = Path(__file__).parent / "testset.json"

# Default system prompt for evaluation — matches the admin global prompt.
_EVAL_SYSTEM_PROMPT = """\
Ты -- ассистент для HR-специалистов компании Кафетера. Помогай разбираться \
во всей базе знаний HR-документов. Отвечай на любые вопросы, опираясь на \
все доступные документы.

Правила:
- Отвечай кратко, структурированно и по существу.
- Используй списки и нумерацию для пошаговых ответов.
- Если в базе знаний недостаточно информации для полного ответа -- \
скажи об этом прямо и укажи, что база знаний не содержит достаточно данных.
- Допускай общие пояснения и синтез информации из разных документов, \
если это помогает дать полный ответ.
- При цитировании или использовании информации из конкретного документа — \
указывай его название.
- Отвечай на русском языке.

Контекст из всех доступных документов:
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


def _build_ragas_llm(settings: RagServiceSettings):
    """Build a RAGAS evaluator LLM backed by Ollama via OpenAI-compatible API."""
    async_client = AsyncOpenAI(
        base_url=f"{settings.llm_base_url}/v1",
        api_key="ollama",
    )
    return llm_factory(
        model=settings.llm_model,
        provider="openai",
        client=async_client,
    )


def _build_ragas_embeddings(settings: RagServiceSettings):
    """Build RAGAS embeddings backed by Ollama via OpenAI-compatible API."""
    async_client = AsyncOpenAI(
        base_url=f"{settings.embedding_base_url}/v1",
        api_key="ollama",
    )
    return embedding_factory(
        provider="openai",
        model=settings.embedding_model,
        client=async_client,
        interface="modern",
    )


async def _collect_answers(
    samples: list[dict[str, Any]],
    settings: RagServiceSettings,
) -> list[dict[str, Any]]:
    """Run each testset question through QAService and collect answers + contexts."""
    res = await build_rag_resources(settings)
    try:
        qa = build_qa_service(res, _EVAL_SYSTEM_PROMPT)

        results: list[dict[str, Any]] = []
        for i, sample in enumerate(samples):
            question = sample.get("user_input", "")
            if not question:
                logger.warning("Sample %d has no user_input, skipping", i)
                continue

            logger.info("[%d/%d] Asking: %s", i + 1, len(samples), question[:80])
            try:
                answer, contexts = await qa.ask_with_contexts(question)
            except Exception:
                logger.exception("Failed on sample %d", i)
                answer, contexts = "", []

            results.append({
                "user_input": question,
                "response": answer,
                "retrieved_contexts": contexts,
                # Preserve reference if present in testset (for ContextRecall)
                **({"reference": sample["reference"]} if "reference" in sample else {}),
            })

        return results
    finally:
        await close_rag_resources(res)


async def _score_metrics(
    results: list[dict[str, Any]],
    settings: RagServiceSettings,
) -> list[dict[str, Any]]:
    """Score each result with RAGAS metrics (collections API).

    Returns a list of per-sample score dicts.
    """
    ragas_llm = _build_ragas_llm(settings)
    ragas_embeddings = _build_ragas_embeddings(settings)

    has_reference = all("reference" in r and r["reference"] for r in results)

    faithfulness = Faithfulness(llm=ragas_llm)
    context_precision = ContextPrecisionWithoutReference(llm=ragas_llm)
    answer_relevancy = AnswerRelevancy(
        llm=ragas_llm, embeddings=ragas_embeddings,
    )
    context_recall = ContextRecall(llm=ragas_llm) if has_reference else None

    scores: list[dict[str, Any]] = []

    for i, r in enumerate(results):
        row_scores: dict[str, Any] = {"user_input": r["user_input"]}

        # Faithfulness
        try:
            result = await faithfulness.ascore(
                user_input=r["user_input"],
                response=r["response"],
                retrieved_contexts=r["retrieved_contexts"],
            )
            row_scores["faithfulness"] = result.value
        except Exception:
            logger.exception("Faithfulness failed for sample %d", i)
            row_scores["faithfulness"] = None

        # Context Precision (without reference)
        try:
            result = await context_precision.ascore(
                user_input=r["user_input"],
                response=r["response"],
                retrieved_contexts=r["retrieved_contexts"],
            )
            row_scores["context_precision"] = result.value
        except Exception:
            logger.exception("ContextPrecision failed for sample %d", i)
            row_scores["context_precision"] = None

        # Answer Relevancy
        try:
            result = await answer_relevancy.ascore(
                user_input=r["user_input"],
                response=r["response"],
            )
            row_scores["answer_relevancy"] = result.value
        except Exception:
            logger.exception("AnswerRelevancy failed for sample %d", i)
            row_scores["answer_relevancy"] = None

        # Context Recall (only if references exist)
        if context_recall is not None:
            try:
                result = await context_recall.ascore(
                    user_input=r["user_input"],
                    retrieved_contexts=r["retrieved_contexts"],
                    reference=r["reference"],
                )
                row_scores["context_recall"] = result.value
            except Exception:
                logger.exception("ContextRecall failed for sample %d", i)
                row_scores["context_recall"] = None

        scores.append(row_scores)
        logger.info(
            "[%d/%d] %s",
            i + 1,
            len(results),
            {k: f"{v:.3f}" if isinstance(v, float) else v for k, v in row_scores.items()},
        )

    return scores


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
    """Main evaluation pipeline."""
    settings = RagServiceSettings()

    # 1. Load testset
    samples = _load_testset(testset_path)
    logger.info("Loaded %d samples from %s", len(samples), testset_path)

    # 2. Collect answers from RAG pipeline
    logger.info("Collecting answers from RAG pipeline...")
    results = await _collect_answers(samples, settings)

    if not results:
        logger.error("No results collected. Check RAG service and Qdrant.")
        sys.exit(1)

    # 3. Score with RAGAS metrics
    logger.info("Scoring with RAGAS metrics...")
    scores = await _score_metrics(results, settings)

    # 4. Print results
    _print_summary(scores)

    # 5. Save detailed scores
    output_path = testset_path.parent / "scores.json"
    output_path.write_text(
        json.dumps(scores, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
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
