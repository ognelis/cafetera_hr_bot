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
from ragas.run_config import RunConfig
from ragas.testset import TestsetGenerator
from ragas.testset.graph import KnowledgeGraph, Node, NodeType
from ragas.testset.transforms.default import default_transforms_for_prechunked
from ragas.testset.transforms.engine import apply_transforms

from cafetera_rag_service.config import RagServiceSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TESTSET_PATH = Path(__file__).parent / "testset.json"


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
_LLM_MAX_TOKENS = 4096
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
    return llm_factory(
        model=settings.llm_model,
        provider="openai",
        client=client,
        max_tokens=_LLM_MAX_TOKENS,
        temperature=_LLM_TEMPERATURE,
    )


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


def _generate_with_nan_filter(
    generator: TestsetGenerator,
    *,
    testset_size: int,
) -> Any:
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

    # 4. Generate testset from the populated knowledge graph
    generator = TestsetGenerator(
        llm=ragas_llm,
        embedding_model=ragas_embeddings,
        knowledge_graph=kg,
    )
    # Request extra samples to compensate for expected NaN failures from the
    # local LLM.  We ask for 2x the desired size and trim later.
    request_size = size * 2
    logger.info(
        "Generating %d synthetic test samples (requesting %d to account for LLM failures)...",
        size,
        request_size,
    )

    try:
        testset = _generate_with_nan_filter(
            generator,
            testset_size=request_size,
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
        default=20,
        help="Number of test samples to generate (default: 20)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    generate_testset(size=args.size)
