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
    """
    res = RagResources(settings=settings)

    # 1. Qdrant + embeddings
    qdrant_client = build_qdrant_client(settings)
    embeddings = build_embeddings(settings)
    res.qdrant_client = qdrant_client
    res.embeddings = embeddings

    # 2. Sparse embeddings (optional)
    res.sparse_embeddings = build_sparse_embeddings(settings)

    # 3. Reranker (optional)
    reranker, reranker_http = build_reranker(settings)
    res.reranker = reranker
    res.reranker_http_client = reranker_http

    # 4. LLM
    res.llm = build_llm(settings)

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
# until max_tokens is exhausted, producing invalid JSON.
_LLM_MAX_TOKENS = 65536


def _build_ragas_llm(settings: RagServiceSettings):
    """Build a RAGAS evaluator LLM from configured provider."""
    provider = settings.llm_provider.lower()
    if provider == "openai":
        base_url = settings.llm_base_url  # already includes /v1
        api_key = settings.llm_api_key
    elif provider == "llamacpp":
        base_url = f"{settings.llm_base_url}/v1"
        api_key = "no-key"
    else:  # ollama (default)
        base_url = f"{settings.llm_base_url}/v1"
        api_key = "ollama"

    async_client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    ragas_llm = llm_factory(
        model=settings.llm_model,
        provider="openai",
        client=async_client,
    )

    # Inject extra_body into the instructor client's default kwargs so that
    # every chat.completions.create() call includes the context window hint
    # and repetition penalty controls.
    # RAGAS's InstructorLLM stores extra_body in model_args but the instructor
    # layer may not forward it reliably; setting it on client.kwargs uses
    # instructor's own handle_kwargs() merge which is guaranteed to apply.
    extra_body: dict[str, Any] = {}
    if provider == "ollama":
        extra_body = {"options": {}}
        if settings.llm_num_ctx:
            extra_body["options"]["num_ctx"] = settings.llm_num_ctx
    elif provider == "llamacpp":
        if settings.llm_num_ctx:
            extra_body["n_ctx"] = settings.llm_num_ctx

    ragas_llm.client.kwargs["max_tokens"] = _LLM_MAX_TOKENS
    if extra_body:
        ragas_llm.client.kwargs["extra_body"] = extra_body

    return ragas_llm


def _build_ragas_embeddings(settings: RagServiceSettings):
    """Build RAGAS embeddings from configured provider."""
    provider = settings.embedding_provider.lower()
    if provider == "openai":
        base_url = settings.embedding_base_url
        api_key = settings.embedding_api_key
    elif provider == "llamacpp":
        base_url = settings.embedding_base_url  # already includes /v1
        api_key = "no-key"
    else:  # ollama (default)
        base_url = f"{settings.embedding_base_url}/v1"
        api_key = "ollama"

    async_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
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
    res = await build_ragas_resources(settings)
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
