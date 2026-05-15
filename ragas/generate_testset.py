"""Generate synthetic QA testset from Qdrant document chunks using RAGAS.

Connects to Qdrant, reads all stored chunks from the configured collection,
and uses RAGAS TestsetGenerator with the configured LLM provider to produce
synthetic question-answer pairs for RAG evaluation.

Usage:
    uv run python ragas/generate_testset.py --size 20
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
from langchain_core.documents import Document as LCDocument
from openai import OpenAI
from qdrant_client import QdrantClient
from ragas.embeddings.base import embedding_factory
from ragas.executor import Executor
from ragas.llms import llm_factory
from ragas.llms.base import BaseRagasLLM
from ragas.run_config import RunConfig
from ragas.testset import Testset, TestsetGenerator
from ragas.testset.graph import KnowledgeGraph, Node, NodeType
from ragas.testset.persona import Persona
from ragas.testset.synthesizers import QueryDistribution, default_query_distribution
from ragas.testset.synthesizers.multi_hop.prompts import (
    QueryAnswerGenerationPrompt as MultiHopQAGenPrompt,
)
from ragas.testset.synthesizers.single_hop.prompts import (
    QueryAnswerGenerationPrompt as SingleHopQAGenPrompt,
)
from ragas.testset.transforms.default import default_transforms_for_prechunked
from ragas.testset.transforms.engine import apply_transforms

from cafetera_rag_service.config import RagServiceSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TESTSET_PATH = Path(__file__).parent / "testset.json"

# Reference (golden) answer instruction shared by single-hop and multi-hop
# synthesizers. Overrides the default RAGAS prompts to bias toward longer,
# fully-grounded HR-style answers in Russian.
_DETAILED_RU_QA_INSTRUCTION = (
    "Сгенерируй пару (вопрос, ответ) строго на основе переданного контекста.\n\n"
    "Требования к ВОПРОСУ:\n"
    "1. Вопрос должен быть конкретным — контекст даёт на него однозначный ответ.\n"
    "2. Формулируй естественно, как реальный сотрудник: без канцеляризмов.\n"
    "3. Не упоминай названия документов в вопросе.\n\n"
    "Требования к ОТВЕТУ (reference):\n"
    "1. Длина соответствует сложности вопроса: простой факт — 1–2 предложения, "
    "сложная процедура — 3–5 предложений. Не растягивай ответ искусственно.\n"
    "2. Ответ обязан быть полностью обоснован переданным контекстом — "
    "не выдумывай фактов.\n"
    "3. Включай все релевантные детали: условия, сроки, ответственных, "
    "исключения — но только если они есть в контексте.\n"
    "4. Стиль — деловой, как ответ опытного HR-сотрудника коллеге.\n"
    "5. Не используй метафразы: 'согласно контексту', 'в документе сказано', "
    "'на основании предоставленной информации', 'исходя из текста'.\n"
    "6. Пиши обычным текстом — без жирного выделения, без маркированных "
    "списков, если вопрос не требует перечисления шагов.\n"
)

_DETAILED_EN_QA_INSTRUCTION = (
    "Generate a question-answer pair in English based strictly on the provided "
    "context.\n\n"
    "Question requirements:\n"
    "1. The question must be specific — the context provides a clear answer.\n"
    "2. Phrase it naturally, as a real employee would ask.\n"
    "3. Do not mention document names in the question.\n\n"
    "Answer requirements:\n"
    "1. Length matches complexity: simple fact — 1–2 sentences, "
    "complex procedure — 3–5 sentences. Do not pad unnecessarily.\n"
    "2. Ground every statement in the provided context — no invented facts.\n"
    "3. Include all relevant details: conditions, deadlines, responsible "
    "parties, exceptions — only if present in the context.\n"
    "4. Style: professional, supportive, no bureaucratic language.\n"
    "5. Avoid meta-phrases: 'according to the context', 'the document states', "
    "'based on the provided information'.\n"
    "6. Plain text only — no bold, no bullet lists unless listing steps.\n"
)


class DetailedSingleHopQAPrompt(SingleHopQAGenPrompt):
    instruction = _DETAILED_RU_QA_INSTRUCTION

    def __init__(self) -> None:
        # ``BasePrompt.__init__`` derives ``name`` from the class name, which
        # would change the key used by ``set_prompts`` / ``get_prompts``.
        # Pin it back to the canonical name after super init.
        super().__init__()
        self.name = "query_answer_generation_prompt"


class DetailedMultiHopQAPrompt(MultiHopQAGenPrompt):
    # Multi-hop требует явного указания на синтез нескольких фактов
    instruction = (
        _DETAILED_RU_QA_INSTRUCTION
        + "\n7. Вопрос должен требовать объединения информации из нескольких "
        "частей контекста — не задавай вопрос, ответ на который содержится "
        "в одном предложении.\n"
        "8. Ответ явно связывает факты из разных частей контекста.\n"
    )

    def __init__(self) -> None:
        super().__init__()
        self.name = "query_answer_generation_prompt"


# Explicit HR-bot personas steer both question phrasing and answer style.
# Without ``persona_list`` RAGAS auto-generates generic personas from the KG via
# ``PersonasGenerationPrompt`` — replacing them with role-specific HR askers
# typically lengthens answers and surfaces realistic phrasing patterns.
HR_PERSONAS: list[Persona] = [
    Persona(
        name="Новый сотрудник кофейни",
        role_description=(
            "Бариста на испытательном сроке (первые 3 месяца). Задаёт "
            "развёрнутые вопросы про оформление, график, обучение, оплату. "
            "Пишет разговорно, иногда с опечатками или без знаков препинания. "
            "Ожидает пошаговые ответы с конкретными условиями и сроками."
        ),
    ),
    Persona(
        name="Опытный сотрудник",
        role_description=(
            "Работает более года, знает базовые правила. Задаёт точечные "
            "уточняющие вопросы про отпуска, переводы, материальную "
            "ответственность, увольнение. Пишет грамотно и формально. "
            "Ожидает краткие точные ответы с указанием конкретных норм."
        ),
    ),
    Persona(
        name="Менеджер смены",
        role_description=(
            "Руководит командой из 3–8 человек. Задаёт вопросы про "
            "дисциплинарные процедуры, оформление нарушений, права при "
            "конфликтах, документооборот. Пишет чётко и структурированно. "
            "Ожидает ответы со ссылкой на конкретный регламент или пункт."
        ),
    ),
    Persona(
        name="Иностранный сотрудник",
        role_description=(
            "Expat or foreign national working at the coffee shop. Asks "
            "questions in English about working conditions, leave policy, "
            "labor rights, and HR procedures. Uses simple, direct phrasing. "
            "Expects clear answers in English with key Russian terms in "
            "parentheses where relevant."
        ),
    ),
]


def _load_settings() -> RagServiceSettings:
    """Load RAG service settings from .env."""
    return RagServiceSettings()


def _scroll_all_points(
    client: QdrantClient,
    collection_name: str,
    batch_size: int = 100,
) -> list[dict[str, Any]]:
    """Scroll through all points in a Qdrant collection.

    Returns a list of dicts with 'page_content' and 'metadata' keys.
    """
    points: list[dict[str, Any]] = []
    offset = None

    while True:
        result = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        batch, next_offset = result

        for point in batch:
            payload = point.payload or {}
            page_content = payload.get("page_content", "")
            if not page_content or not page_content.strip():
                continue
            metadata = payload.get("metadata", {})
            points.append({
                "page_content": page_content,
                "metadata": metadata,
            })

        if next_offset is None:
            break
        offset = next_offset

    return points


def _build_langchain_docs(raw_points: list[dict[str, Any]]) -> list[LCDocument]:
    """Convert raw Qdrant payloads to LangChain Document objects."""
    docs: list[LCDocument] = []
    for pt in raw_points:
        docs.append(
            LCDocument(
                page_content=pt["page_content"],
                metadata=pt.get("metadata", {}),
            )
        )
    return docs


# -- LLM tuning for local models -------------------------------------------------
# Small local models (e.g. T-lite q4) are prone to repetition loops that exhaust
# the default max_tokens budget before producing valid structured JSON.  Raising
# max_tokens gives the model room to finish, and lowering temperature reduces
# degenerate repetitions.
_LLM_MAX_TOKENS = 65536
_LLM_TEMPERATURE = 0.2


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

    client = OpenAI(base_url=base_url, api_key=api_key)
    llm = llm_factory(
        model=settings.llm_model,
        provider="openai",
        client=client,
        max_tokens=_LLM_MAX_TOKENS,
        temperature=_LLM_TEMPERATURE,
    )

    # For llamacpp provider, also set n_predict in extra_body
    # (llama.cpp default is often 2048-4096, independent of max_tokens)
    if provider == "llamacpp":
        extra_body = {}
        if settings.llm_num_ctx:
            extra_body["n_ctx"] = settings.llm_num_ctx
        extra_body["n_predict"] = settings.llm_max_tokens
        llm.client.kwargs["extra_body"] = extra_body

    return llm


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

    client = OpenAI(base_url=base_url, api_key=api_key)
    return embedding_factory(
        provider="openai",
        model=settings.embedding_model,
        client=client,
        interface="modern",
    )


def _is_nan(value: Any) -> bool:
    """Check if a value is NaN (float or numpy)."""
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        return bool(np.isnan(value))
    except (TypeError, ValueError):
        return False


def _nan_filtering_results(original_results):
    """Wrap ``Executor.results`` to silently drop NaN entries.

    RAGAS ``Executor`` stores ``np.nan`` for jobs that fail when
    ``raise_exceptions=False``.  The default ``generate()`` then tries to
    wrap every result in ``TestsetSample`` which crashes on NaN.
    """

    def patched_results(self: Executor) -> list[Any]:
        raw = original_results(self)
        valid = [r for r in raw if not _is_nan(r)]
        n_dropped = len(raw) - len(valid)
        if n_dropped:
            logger.warning(
                "Filtered %d NaN sample(s) from %d total executor results",
                n_dropped,
                len(raw),
            )
        return valid

    return patched_results


def _build_query_distribution(
    llm: BaseRagasLLM, kg: KnowledgeGraph
) -> QueryDistribution:
    """Build the default query distribution with HR-tuned reference prompts.

    Reuses ``default_query_distribution`` so we keep RAGAS' default
    synthesizer set and weights, then patches the
    ``query_answer_generation_prompt`` on each synthesizer with our detailed
    Russian HR instruction.  Dispatch is by ``isinstance`` of the existing
    prompt so this stays correct if RAGAS adds more synthesizers later.
    """
    distribution = default_query_distribution(llm, kg)
    for synth, _weight in distribution:
        existing = synth.get_prompts().get("query_answer_generation_prompt")
        if isinstance(existing, MultiHopQAGenPrompt):
            synth.set_prompts(query_answer_generation_prompt=DetailedMultiHopQAPrompt())
        elif isinstance(existing, SingleHopQAGenPrompt):
            synth.set_prompts(query_answer_generation_prompt=DetailedSingleHopQAPrompt())
    return distribution


def _generate_with_nan_filter(
    generator: TestsetGenerator,
    *,
    testset_size: int,
    query_distribution: QueryDistribution | None = None,
) -> Testset:
    """Run ``generator.generate()`` with NaN-safe sample filtering.

    Monkey-patches ``Executor.results`` for the duration of the call so
    that any ``np.nan`` produced by the local LLM is dropped before RAGAS
    tries to construct ``TestsetSample`` objects.

    Note: ``generate()`` builds ``additional_testset_info`` in lock-step
    with submitted jobs.  After filtering, the two lists may be
    positionally misaligned — ``zip()`` will silently truncate the
    longer one.  The only affected field is ``synthesizer_name`` which is
    informational and does not affect evaluation scoring.
    """
    original_results = Executor.results
    patched = _nan_filtering_results(original_results)

    with patch.object(Executor, "results", patched):
        testset = generator.generate(
            testset_size=testset_size,
            raise_exceptions=False,
            query_distribution=query_distribution,
        )

    return testset


def generate_testset(size: int = 20) -> None:
    """Generate a synthetic testset and save it to disk."""
    settings = _load_settings()

    # 1. Connect to Qdrant (sync client for scrolling)
    logger.info(
        "Connecting to Qdrant at %s, collection '%s'",
        settings.qdrant_url,
        settings.qdrant_collection,
    )
    qdrant = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=settings.qdrant_timeout,
    )

    try:
        raw_points = _scroll_all_points(qdrant, settings.qdrant_collection)
    finally:
        qdrant.close()

    if not raw_points:
        logger.error(
            "No documents found in collection '%s'. "
            "Upload and index documents first.",
            settings.qdrant_collection,
        )
        sys.exit(1)

    logger.info("Loaded %d chunks from Qdrant", len(raw_points))
    docs = _build_langchain_docs(raw_points)

    # 2. Build RAGAS LLM and embeddings
    logger.info("Initializing RAGAS LLM (%s) and embeddings", settings.llm_model)
    ragas_llm = _build_ragas_llm(settings)
    ragas_embeddings = _build_ragas_embeddings(settings)

    # 3. Build knowledge graph with CHUNK nodes.
    # generate_with_langchain_docs creates DOCUMENT nodes, but
    # default_transforms_for_prechunked filters on NodeType.CHUNK,
    # so all extractors would process 0 items. Build the KG manually.
    nodes = [
        Node(
            type=NodeType.CHUNK,
            properties={
                "page_content": doc.page_content,
                "document_metadata": doc.metadata,
            },
        )
        for doc in docs
    ]
    kg = KnowledgeGraph(nodes=nodes)

    transforms = default_transforms_for_prechunked(
        llm=ragas_llm,
        embedding_model=ragas_embeddings,
    )
    logger.info("Applying transforms to %d CHUNK nodes...", len(nodes))
    apply_transforms(kg, transforms, run_config=RunConfig())

    # 4. Generate testset from the populated knowledge graph.
    # ``persona_list`` overrides RAGAS's auto-generated personas with explicit
    # HR-bot askers so question phrasing and answer style match real users.
    generator = TestsetGenerator(
        llm=ragas_llm,
        embedding_model=ragas_embeddings,
        knowledge_graph=kg,
        persona_list=HR_PERSONAS,
    )
    # Request extra samples to compensate for expected NaN failures from the
    # local LLM.  We ask for 2x the desired size and trim later.
    request_size = size
    logger.info(
        "Generating %d synthetic test samples (requesting %d to account for LLM failures)...",
        size,
        request_size,
    )

    # Override per-synthesizer reference-answer prompts to produce longer,
    # HR-style Russian golden answers.
    query_distribution = _build_query_distribution(ragas_llm, kg)

    try:
        testset = _generate_with_nan_filter(
            generator,
            testset_size=request_size,
            query_distribution=query_distribution,
        )
    except Exception:
        logger.exception("Testset generation failed")
        sys.exit(1)

    # 5. Save to JSON — trim to the originally requested size
    samples = testset.to_list()[:size]
    if not samples:
        logger.error("No samples were generated. Try increasing --size or check LLM.")
        sys.exit(1)

    TESTSET_PATH.write_text(
        json.dumps(samples, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved %d samples to %s", len(samples), TESTSET_PATH)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic QA testset from Qdrant chunks",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=40,
        help="Number of test samples to generate (default: 20)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    generate_testset(size=args.size)
