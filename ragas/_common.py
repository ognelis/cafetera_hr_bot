"""Shared infrastructure for RAGAS evaluation scripts.

Provides resource builders, LLM/embedding factories, testset loading,
and summary output used by both ``evaluate.py`` and ``optimize_prompt.py``.
"""

from __future__ import annotations

import json
import logging
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
from openai import AsyncOpenAI
from ragas import EvaluationDataset, RunConfig, aevaluate
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory

# NOTE: ``aevaluate()`` (ragas 0.4.x) only accepts classic metric objects that
# subclass ``ragas.metrics.base.Metric``.  The newer ``ragas.metrics.collections``
# classes do NOT inherit from it and raise ``TypeError: All metrics must be
# initialised metric objects``.  Until ``aevaluate()`` is migrated to the new
# collections API (or we drop it for @experiment-based scoring), import the
# legacy metric classes here.  They emit an import-time DeprecationWarning that
# is attributed to *this* module via ``stacklevel>=2``; filter by category alone
# — ``module="ragas"`` would miss it.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from ragas.metrics import (  # noqa: E402
        AnswerRelevancy as _AnswerRelevancy,
    )
    from ragas.metrics import (  # noqa: E402
        Faithfulness as _Faithfulness,
    )
    from ragas.metrics import (  # noqa: E402
        LLMContextPrecisionWithoutReference as _ContextPrecisionWithoutReference,
    )
    from ragas.metrics import (  # noqa: E402
        NonLLMContextRecall as _NonLLMContextRecall,
    )
    from ragas.metrics import (  # noqa: E402
        SemanticSimilarity as _SemanticSimilarity,
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
    build_reranker,
    close_rag_resources,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TESTSET = Path(__file__).parent / "testset.json"

# Concurrency limiter for QA-phase rows — prevents overwhelming the local LLM
# and keeps peak RAM bounded (only N answer+context sets in flight at once).
MAX_CONCURRENT_QA = 2

# Max workers for aevaluate() scoring phase.
MAX_SCORING_WORKERS = 3

# Faithfulness needs a generous max_tokens ceiling (NER extraction produces
# long JSON).  All other metrics emit short verdicts.  Since aevaluate()
# uses a single LLM, we set it to the Faithfulness budget.
EVALUATOR_MAX_TOKENS = 16384

# Default system prompt for evaluation — matches the admin global prompt.
EVAL_SYSTEM_PROMPT = """\
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


# ---------------------------------------------------------------------------
# Resource infrastructure
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# LLM / embedding builder helpers for local models
# ---------------------------------------------------------------------------
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


def resolve_llm_endpoint(
    settings: RagServiceSettings,
) -> tuple[str, str, str]:
    """Return (base_url, api_key, provider) for the LLM endpoint."""
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return settings.llm_base_url, settings.llm_api_key, provider
    if provider == "llamacpp":
        return f"{settings.llm_base_url}/v1", "no-key", provider
    return f"{settings.llm_base_url}/v1", "ollama", provider  # ollama default


def resolve_embedding_endpoint(
    settings: RagServiceSettings,
) -> tuple[str, str]:
    """Return (base_url, api_key) for the embedding endpoint."""
    provider = settings.embedding_provider.lower()
    if provider == "openai":
        return settings.embedding_base_url, settings.embedding_api_key
    if provider == "llamacpp":
        return settings.embedding_base_url, "no-key"
    return f"{settings.embedding_base_url}/v1", "ollama"  # ollama default


def get_async_client(
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


def build_ragas_llm(
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
    base_url, api_key, provider = resolve_llm_endpoint(settings)
    async_client = get_async_client(base_url, api_key, client_cache)

    ragas_llm = llm_factory(
        model=settings.llm_model,
        provider="openai",
        client=async_client,
    )

    # Inject extra_body into the instructor client's default kwargs so that
    # every chat.completions.create() call includes the context window hint
    # and generation cap.
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


def build_ragas_embeddings(
    settings: RagServiceSettings,
    client_cache: dict[tuple[str, str], AsyncOpenAI],
    *,
    interface: str = "modern",
):
    """Build RAGAS embeddings from configured provider.

    ``interface`` selects which RAGAS embedding abstraction to return:

    - ``"modern"`` (default) — returns ``OpenAIEmbeddings`` with ``.embed_text()``,
      required by ``ragas.metrics.collections.*`` metrics (used by
      ``optimize_prompt.py``).
    - ``"legacy"`` — returns ``LangchainEmbeddingsWrapper`` with ``.embed_query()``,
      required by legacy ``ragas.metrics.*`` metrics (used by ``evaluate.py``
      because ``aevaluate()`` in ragas 0.4.x only accepts legacy metric classes).
    """
    base_url, api_key = resolve_embedding_endpoint(settings)
    async_client = get_async_client(base_url, api_key, client_cache)

    if interface == "legacy":
        # ragas 0.4.3's ``embedding_factory`` legacy branch builds
        # ``langchain_openai.OpenAIEmbeddings(model=..., base_url=...)`` without
        # propagating ``api_key`` or the pre-built client, which fails on local
        # llama.cpp / Ollama endpoints that have no ``OPENAI_API_KEY``.  Build
        # the wrapper ourselves so the configured credentials and the shared
        # ``AsyncOpenAI`` pool are honoured.
        from langchain_openai import OpenAIEmbeddings as LCOpenAIEmbeddings
        from ragas.embeddings.base import LangchainEmbeddingsWrapper

        lc_embeddings = LCOpenAIEmbeddings(
            model=settings.embedding_model,
            base_url=base_url,
            api_key=api_key,
            async_client=async_client.embeddings,
            check_embedding_ctx_length=False,
        )
        return LangchainEmbeddingsWrapper(lc_embeddings)

    return embedding_factory(
        provider="openai",
        model=settings.embedding_model,
        client=async_client,
        interface=interface,
    )


# ---------------------------------------------------------------------------
# Testset loading
# ---------------------------------------------------------------------------


def load_testset(path: Path) -> list[dict[str, Any]]:
    """Load testset JSON and return list of sample dicts."""
    if not path.exists():
        logger.error("Testset not found at %s. Run generate_testset.py first.", path)
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        logger.error("Testset at %s is empty or not a list.", path)
        sys.exit(1)

    return data


# ---------------------------------------------------------------------------
# RAGAS metric composition + scoring (shared between evaluate.py and
# optimize_prompt.py)
# ---------------------------------------------------------------------------


def build_eval_metrics(
    ragas_llm: Any,
    ragas_embeddings: Any,
    *,
    has_reference_contexts: bool = False,
    has_reference: bool = False,
) -> list[Any]:
    """Build the canonical RAGAS legacy-metric set for ``aevaluate()``.

    Always includes ``Faithfulness``, ``LLMContextPrecisionWithoutReference``,
    and ``AnswerRelevancy``.  Conditionally appends zero-LLM deterministic
    metrics when the testset provides ground truth:

    - ``NonLLMContextRecall`` when ``has_reference_contexts`` is set —
      string-similarity match between ``reference_contexts`` and
      ``retrieved_contexts`` (default threshold 0.5).  Replaces the legacy
      LLM-judged ``ContextRecall`` which small local models cannot produce
      reliably (Qwen3.5-9B-Q4_K_M schema-echoes the nested classifications
      schema).
    - ``SemanticSimilarity`` when ``has_reference`` is set — cosine similarity
      between embeddings of ``response`` and ``reference``.  Provides a
      fully deterministic answer-quality signal that complements the noisy
      LLM-judged ``AnswerRelevancy`` on small local evaluator models.
    """
    metrics: list[Any] = [
        _Faithfulness(llm=ragas_llm),
        _ContextPrecisionWithoutReference(llm=ragas_llm),
        _AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
    ]
    if has_reference_contexts:
        metrics.append(_NonLLMContextRecall())
    if has_reference:
        metrics.append(_SemanticSimilarity(embeddings=ragas_embeddings))
    return metrics


async def score_with_metrics(
    eval_dataset: EvaluationDataset,
    metrics: list[Any],
    *,
    experiment_name: str | None = None,
) -> Any:
    """Run ``aevaluate()`` with project-standard configuration.

    Centralises the scoring-phase contract used by both ``evaluate.py`` and
    ``optimize_prompt.py``:

    - ``RunConfig(max_workers=MAX_SCORING_WORKERS)`` — bounded metric
      concurrency so the local evaluator LLM stays within its slot budget.
    - ``raise_exceptions=False`` — per-cell failures become ``NaN`` in the
      returned ``EvaluationResult`` instead of aborting the whole run.
    - ``DeprecationWarning`` suppression — ``aevaluate()`` emits its
      removal-notice warning with ``stacklevel>=2``, so the warning is
      attributed to the *caller*, not to ``ragas.*``.  Filter by category
      alone; the ``with`` scope covers only the ``aevaluate()`` call.

    Returns the ``EvaluationResult`` produced by ``aevaluate()``.
    """
    kwargs: dict[str, Any] = {
        "dataset": eval_dataset,
        "metrics": metrics,
        "run_config": RunConfig(max_workers=MAX_SCORING_WORKERS),
        "raise_exceptions": False,
    }
    if experiment_name:
        kwargs["experiment_name"] = experiment_name

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        return await aevaluate(**kwargs)


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


def print_summary(result: Any) -> None:
    """Print aggregate summary table from aevaluate results.

    Derives metric names from the scores dicts (avoids hardcoding
    and adapts automatically when ContextRecall is absent).
    """
    scores = result.scores
    if not scores:
        return

    # Identify metric columns — any key whose values are numeric.
    metric_names = sorted(
        k for k in scores[0] if isinstance(scores[0][k], (int, float))
    )

    print("\n" + "=" * 60)
    print("RAGAS Evaluation Summary")
    print("=" * 60)

    for metric in metric_names:
        # Build a float array with ``None`` coerced to ``NaN`` so numpy's
        # ``nan*`` family can handle both missing values (metric absent on row)
        # and failed rows (instructor parse failures — ragas already stores
        # these as ``NaN``).  This mirrors ragas's own top-line aggregation
        # (``nanmean``) and avoids manual filtering.
        raw = [s.get(metric) for s in scores]
        arr = np.array(
            [np.nan if v is None else v for v in raw],
            dtype=float,
        )
        n_valid = int(np.count_nonzero(~np.isnan(arr)))
        if n_valid:
            print(
                f"  {metric:<40s}  "
                f"avg={np.nanmean(arr):.3f}  "
                f"min={np.nanmin(arr):.3f}  "
                f"max={np.nanmax(arr):.3f}  "
                f"n={n_valid}/{len(scores)}"
            )
        else:
            print(f"  {metric:<40s}  NO VALID SCORES")

    print("=" * 60)
