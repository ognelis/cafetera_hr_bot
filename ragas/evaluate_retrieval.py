"""Evaluate retrieval quality using SberQuAD benchmark.

Starts a temporary Qdrant container, indexes SberQuAD contexts,
retrieves for each question, and computes offline retrieval metrics
(MRR, NDCG, Hit Rate, Recall, Precision).

Usage:
    uv run python ragas/evaluate_retrieval.py
    uv run python ragas/evaluate_retrieval.py --k 5 --size 200
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import logging
import re
import subprocess
import time
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
from langchain_core.documents import Document
from qdrant_client import AsyncQdrantClient, models

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.rag.retriever import (
    AsyncQdrantRetriever,
    build_embeddings,
    build_sparse_embeddings,
)
from cafetera_rag_service.resources import build_reranker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "sberquad_eval"
BATCH_SIZE = 64
HEALTHZ_RETRIES = 30
HEALTHZ_INTERVAL = 1.0


# ---------------------------------------------------------------------------
# 1. Temporary Qdrant container helpers
# ---------------------------------------------------------------------------

def _start_qdrant_container() -> tuple[str, str]:
    """Start a temporary Qdrant container with a random host port.

    Returns (container_id, qdrant_url).
    """
    result = subprocess.run(
        ["docker", "run", "-d", "--rm", "-p", "0:6333", "qdrant/qdrant:latest"],
        capture_output=True,
        text=True,
        check=True,
    )
    container_id = result.stdout.strip()
    logger.info("Started Qdrant container %s", container_id[:12])

    # Discover assigned host port
    port_result = subprocess.run(
        ["docker", "port", container_id, "6333"],
        capture_output=True,
        text=True,
        check=True,
    )
    # Output like "0.0.0.0:55123" or "0.0.0.0:55123\n:::55123"
    port_line = port_result.stdout.strip().splitlines()[0]
    match = re.search(r":(\d+)$", port_line)
    if not match:
        raise RuntimeError(f"Cannot parse port from: {port_line}")
    host_port = match.group(1)
    qdrant_url = f"http://localhost:{host_port}"
    logger.info("Qdrant available at %s", qdrant_url)

    # Register cleanup
    def _cleanup() -> None:
        try:
            result = subprocess.run(
                ["docker", "stop", container_id],
                capture_output=True,
                timeout=15,
            )
            if result.returncode == 0:
                logger.info("Stopped Qdrant container %s", container_id[:12])
        except Exception:
            pass

    atexit.register(_cleanup)

    # Wait for Qdrant to become healthy
    _wait_for_healthy(qdrant_url)

    return container_id, qdrant_url


def _wait_for_healthy(qdrant_url: str) -> None:
    """Poll Qdrant /healthz until ready."""
    for attempt in range(HEALTHZ_RETRIES):
        try:
            resp = httpx.get(f"{qdrant_url}/healthz", timeout=2.0)
            if resp.status_code == 200:
                logger.info("Qdrant is healthy (attempt %d)", attempt + 1)
                return
        except httpx.HTTPError:
            pass
        time.sleep(HEALTHZ_INTERVAL)
    raise RuntimeError(f"Qdrant not healthy after {HEALTHZ_RETRIES} attempts")


def _stop_qdrant_container(container_id: str) -> None:
    """Stop the Qdrant container (idempotent)."""
    try:
        result = subprocess.run(
            ["docker", "stop", container_id],
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0:
            logger.info("Stopped Qdrant container %s", container_id[:12])
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 2. SberQuAD loading
# ---------------------------------------------------------------------------

def _load_sberquad(size: int) -> list[dict[str, str]]:
    """Load SberQuAD validation split and return list of {question, context}.

    When size > 0, take only the first `size` samples.
    """
    from datasets import load_dataset

    ds = load_dataset("kuznetsoffandrey/sberquad", split="validation")
    samples: list[dict[str, str]] = []
    for row in ds:
        samples.append({
            "question": row["question"],
            "context": row["context"],
        })
    if size > 0:
        samples = samples[:size]
    logger.info("Loaded %d SberQuAD samples", len(samples))
    return samples


# ---------------------------------------------------------------------------
# 3. Index contexts into temp Qdrant
# ---------------------------------------------------------------------------

def _to_list(value: object) -> list:
    """Convert numpy array or passthrough plain list to Python list."""
    return value.tolist() if hasattr(value, "tolist") else value  # type: ignore[union-attr]


async def _index_contexts(
    unique_contexts: list[str],
    qdrant_url: str,
    embeddings: object | None,
    sparse_embedding: object | None,
    *,
    use_dense: bool = True,
    use_bm25: bool = True,
) -> None:
    """Embed and upsert unique contexts into the temp Qdrant collection."""
    client = AsyncQdrantClient(url=qdrant_url, timeout=120.0)

    try:
        # Build collection config based on mode
        vectors_config: dict | None = None
        sparse_vectors_config: dict | None = None

        if use_dense:
            test_vec = await embeddings.aembed_documents(["test"])  # type: ignore[union-attr]
            vector_size = len(test_vec[0])
            logger.info("Dense vector size: %d", vector_size)
            vectors_config = {
                "dense": models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            }

        if use_bm25:
            sparse_vectors_config = {
                "bm25": models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                    index=models.SparseIndexParams(on_disk=False),
                ),
            }

        # Create collection
        create_kwargs: dict[str, object] = {"collection_name": COLLECTION_NAME}
        if vectors_config:
            create_kwargs["vectors_config"] = vectors_config
        if sparse_vectors_config:
            create_kwargs["sparse_vectors_config"] = sparse_vectors_config
        # Qdrant requires at least vectors_config; for BM25-only use a dummy
        if not vectors_config:
            create_kwargs["vectors_config"] = models.VectorParams(
                size=1, distance=models.Distance.COSINE,
            )
        await client.create_collection(**create_kwargs)  # type: ignore[arg-type]
        logger.info("Created collection '%s'", COLLECTION_NAME)

        # Embed and upsert in batches
        total = len(unique_contexts)
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch_texts = unique_contexts[batch_start:batch_end]

            # Compute embeddings based on mode
            dense_vecs = None
            sparse_results = None

            if use_dense and use_bm25:
                dense_vecs, sparse_results = await asyncio.gather(
                    embeddings.aembed_documents(batch_texts),  # type: ignore[union-attr]
                    asyncio.get_running_loop().run_in_executor(
                        None, sparse_embedding.embed_documents, batch_texts,  # type: ignore[union-attr]
                    ),
                )
            elif use_dense:
                dense_vecs = await embeddings.aembed_documents(batch_texts)  # type: ignore[union-attr]
            else:
                sparse_results = await asyncio.get_running_loop().run_in_executor(
                    None, sparse_embedding.embed_documents, batch_texts,  # type: ignore[union-attr]
                )

            points: list[models.PointStruct] = []
            for i, text in enumerate(batch_texts):
                vector: dict[str, object] = {}
                if dense_vecs is not None:
                    vector["dense"] = _to_list(dense_vecs[i])
                if sparse_results is not None:
                    sr = sparse_results[i]
                    vector["bm25"] = models.SparseVector(
                        indices=_to_list(sr.indices),
                        values=_to_list(sr.values),
                    )
                points.append(
                    models.PointStruct(
                        id=batch_start + i,
                        vector=vector,
                        payload={
                            "page_content": text,
                            "metadata": {"doc_id": batch_start + i},
                        },
                    )
                )

            await client.upsert(collection_name=COLLECTION_NAME, points=points)
            logger.info(
                "Indexed batch %d-%d / %d", batch_start + 1, batch_end, total,
            )
    finally:
        await client.close()

    logger.info("Indexing complete: %d unique contexts", total)


# ---------------------------------------------------------------------------
# 4. Retrieval
# ---------------------------------------------------------------------------

async def _retrieve_all(
    samples: list[dict[str, str]],
    qdrant_url: str,
    settings: RagServiceSettings,
    embeddings: object,
    sparse_embedding: object,
    k: int,
    concurrency: int = 20,
) -> list[list[Document]]:
    """Retrieve top-k documents for every question.
    
    Returns a list parallel to samples, each element is a list[Document].
    Uses semaphore-bounded asyncio.gather for parallel retrieval.
    """

    client = AsyncQdrantClient(url=qdrant_url, timeout=60.0)
    try:
        retriever = AsyncQdrantRetriever(
            client=client,
            collection_name=COLLECTION_NAME,
            embeddings=embeddings,
            sparse_embedding=sparse_embedding,
            lemmatize=settings.bm25_lemmatize,
            k=k,
            score_threshold=settings.dense_score_threshold or None,
            filter=None,
        )

        total = len(samples)
        sem = asyncio.Semaphore(concurrency)
        done = [0]  # mutable counter

        async def _retrieve_one(query: str) -> list[Document]:
            async with sem:
                docs = await retriever.ainvoke(query)
            done[0] += 1
            if done[0] % 50 == 0 or done[0] == total:
                logger.info("Retrieved %d / %d", done[0], total)
            return docs

        tasks = [
            _retrieve_one(sample["question"])
            for sample in samples
        ]
        all_results = await asyncio.gather(*tasks)
        return list(all_results)
    finally:
        await client.close()


async def _apply_reranking(
    samples: list[dict[str, str]],
    results: list[list[Document]],
    settings: RagServiceSettings,
    concurrency: int = 10,
) -> list[list[Document]]:
    """Apply reranker to retrieved results if reranking is enabled.

    Uses semaphore-bounded asyncio.gather for parallel reranking.
    """
    if not settings.reranking_enabled:
        return results

    reranker, http_client = build_reranker(settings)
    if reranker is None:
        return results

    logger.info("Applying reranking (%s)...", settings.reranker_model)
    try:
        total = len(samples)
        sem = asyncio.Semaphore(concurrency)
        done = [0]  # mutable counter

        async def _rerank_one(
            query: str, docs: list[Document],
        ) -> list[Document]:
            async with sem:
                reranked_docs = await reranker.arerank(query, docs)
            done[0] += 1
            if done[0] % 50 == 0 or done[0] == total:
                logger.info("Reranked %d / %d", done[0], total)
            return reranked_docs

        tasks = [
            _rerank_one(sample["question"], docs)
            for sample, docs in zip(samples, results, strict=True)
        ]
        all_reranked = await asyncio.gather(*tasks)
        return list(all_reranked)
    finally:
        if http_client is not None:
            await http_client.aclose()


# ---------------------------------------------------------------------------
# 5. Relevance matching
# ---------------------------------------------------------------------------

def _is_relevant(doc: Document, gold_id: int) -> bool:
    """Exact match against the gold context's point id."""
    return doc.metadata.get("doc_id") == gold_id


# ---------------------------------------------------------------------------
# 6. Metric functions
# ---------------------------------------------------------------------------

def mrr_at_k(relevant_flags: list[bool]) -> float:
    """Mean Reciprocal Rank: 1/rank of first relevant doc, or 0."""
    arr = np.array(relevant_flags)
    indices = np.where(arr)[0]
    if len(indices) == 0:
        return 0.0
    return 1.0 / (indices[0] + 1)


def ndcg_at_k(relevant_flags: list[bool]) -> float:
    """NDCG with binary relevance."""
    arr = np.array(relevant_flags, dtype=np.float64)
    if arr.sum() == 0:
        return 0.0
    positions = np.arange(len(arr)) + 2  # log2(i+2) for i starting from 0
    dcg = float(np.sum(arr / np.log2(positions)))
    # Ideal: all relevant docs at top positions
    n_relevant = int(arr.sum())
    ideal_positions = np.arange(n_relevant) + 2
    idcg = float(np.sum(1.0 / np.log2(ideal_positions)))
    return dcg / idcg


def hit_rate(relevant_flags: list[bool]) -> float:
    """1.0 if any relevant doc found, 0.0 otherwise."""
    return 1.0 if np.any(relevant_flags) else 0.0


def recall_at_k(relevant_flags: list[bool], n_total_relevant: int) -> float:
    """Fraction of total relevant docs found in top-k."""
    if n_total_relevant == 0:
        return 0.0
    return float(np.sum(relevant_flags)) / n_total_relevant


def precision_at_k(relevant_flags: list[bool], k: int) -> float:
    """Standard IR Precision@k: (# relevant in top-k) / k.

    The denominator is the fixed cutoff ``k``, not ``len(relevant_flags)``.
    This is consistent with the textbook definition and ensures comparability
    across retrieval configurations that may return fewer than ``k`` docs
    (e.g., when ``DENSE_SCORE_THRESHOLD`` filters the dense branch).
    """
    if k <= 0:
        return 0.0
    arr = np.asarray(relevant_flags[:k], dtype=np.float64)
    return float(np.sum(arr)) / k


# ---------------------------------------------------------------------------
# 7. CSV output
# ---------------------------------------------------------------------------

def _save_csv(
    samples: list[dict[str, str]],
    all_results: list[list[Document]],
    settings: RagServiceSettings,
    k: int,
    mode: str = "hybrid",
) -> pd.DataFrame:
    """Compute metrics per query and save to CSV. Returns the DataFrame."""
    embedding_model = settings.embedding_model if mode != "bm25-only" else ""
    sparse_model = settings.sparse_embedding_model if mode != "dense-only" else ""
    reranker_model = settings.reranker_model if settings.reranking_enabled else ""

    mrr_col = f"mrr@{k}"
    ndcg_col = f"ndcg@{k}"
    hit_col = f"hit@{k}"
    recall_col = f"recall@{k}"
    precision_col = f"precision@{k}"

    rows: list[dict[str, object]] = []
    for sample, docs in zip(samples, all_results, strict=True):
        gold_id = sample["gold_id"]
        gold_context = sample["context"]
        flags = [_is_relevant(doc, gold_id) for doc in docs]

        rows.append({
            "mode": mode,
            "embedding_model": embedding_model,
            "sparse_model": sparse_model,
            "reranker_model": reranker_model,
            "k": k,
            "question": sample["question"],
            "gold_context_preview": gold_context[:80],
            mrr_col: mrr_at_k(flags),
            ndcg_col: ndcg_at_k(flags),
            hit_col: hit_rate(flags),
            recall_col: recall_at_k(flags, 1),  # SberQuAD has 1 gold context per question
            precision_col: precision_at_k(flags, k),
        })

    df = pd.DataFrame(rows)

    # Add AVERAGE row
    avg_row = {
        "mode": mode,
        "embedding_model": embedding_model,
        "sparse_model": sparse_model,
        "reranker_model": reranker_model,
        "k": k,
        "question": "AVERAGE",
        "gold_context_preview": "",
        mrr_col: df[mrr_col].mean(),
        ndcg_col: df[ndcg_col].mean(),
        hit_col: df[hit_col].mean(),
        recall_col: df[recall_col].mean(),
        precision_col: df[precision_col].mean(),
    }
    df = pd.concat([df, pd.DataFrame([avg_row])], ignore_index=True)

    output_path = Path(__file__).parent / "retrieval_scores.csv"
    df.to_csv(output_path, index=False)
    logger.info("Saved results to %s", output_path)
    return df


# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------

def _print_summary(df: pd.DataFrame, n_questions: int, k: int) -> None:
    """Print a nicely formatted summary to stdout."""
    avg = df.iloc[-1]

    print("\n" + "=" * 64)
    print("  Retrieval Evaluation Summary (SberQuAD)")
    print("=" * 64)
    print(f"  Retrieval mode  : {avg.get('mode', 'hybrid')}")
    print(f"  Embedding model : {avg['embedding_model']}")
    print(f"  Sparse model    : {avg['sparse_model']}")
    reranker_model = avg["reranker_model"]
    print(f"  Reranker model  : {reranker_model if reranker_model else '(disabled)'}")
    print(f"  Questions       : {n_questions}")
    print(f"  Top-k           : {k}")
    print("-" * 64)
    print(f"  {'Metric':<15s}  {'Value':>8s}")
    print("-" * 64)
    for metric in ("mrr", "ndcg", "hit", "recall", "precision"):
        col = f"{metric}@{k}"
        label = f"{metric.upper()}@{k}"
        print(f"  {label:<15s}  {avg[col]:>8.4f}")
    print("=" * 64)

    output_path = Path(__file__).parent / "retrieval_scores.csv"
    print(f"  Results saved to: {output_path}")
    print()


# ---------------------------------------------------------------------------
# 9. CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate retrieval quality on SberQuAD benchmark",
    )
    parser.add_argument(
        "--k", type=int, default=10,
        help=(
            "Retrieval top-k (ignored when RERANKING_ENABLED=true; "
            "RERANKER_PREFETCH_LIMIT is used instead)"
        ),
    )
    parser.add_argument(
        "--size", type=int, default=0,
        help="Number of SberQuAD questions (0=all, default: 500)",
    )
    parser.add_argument(
        "--retrieval-concurrency", type=int, default=10,
        help="Max concurrent retrieval queries (default: 10)",
    )
    parser.add_argument(
        "--rerank-concurrency", type=int, default=2,
        help="Max concurrent reranking requests (default: 2)",
    )
    parser.add_argument(
        "--use-dense", action=argparse.BooleanOptionalAction, default=True,
        help="Enable dense retrieval (default: True)",
    )
    parser.add_argument(
        "--use-bm25", action=argparse.BooleanOptionalAction, default=True,
        help="Enable BM25 sparse retrieval (default: True)",
    )
    args = parser.parse_args()
    if not args.use_dense and not args.use_bm25:
        parser.error("At least one of --use-dense or --use-bm25 must be enabled")
    return args


# ---------------------------------------------------------------------------
# 10. Main async pipeline
# ---------------------------------------------------------------------------

async def evaluate_retrieval(
    k: int,
    size: int,
    retrieval_concurrency: int = 20,
    rerank_concurrency: int = 10,
    *,
    use_dense: bool = True,
    use_bm25: bool = True,
) -> None:
    """End-to-end retrieval evaluation pipeline."""
    settings = RagServiceSettings()

    # Determine retrieval mode label
    if use_dense and use_bm25:
        mode_label = "hybrid"
    elif use_dense:
        mode_label = "dense-only"
    else:
        mode_label = "bm25-only"
    logger.info("Retrieval mode: %s", mode_label)
    print(f"\n  Retrieval mode: {mode_label}")

    # 1. Start temp Qdrant
    container_id, qdrant_url = _start_qdrant_container()

    try:
        # 2. Load SberQuAD
        samples = _load_sberquad(size)

        # Deduplicate contexts for indexing
        context_set: dict[str, int] = {}
        for s in samples:
            ctx = s["context"]
            if ctx not in context_set:
                context_set[ctx] = len(context_set)
        unique_contexts = list(context_set.keys())
        logger.info(
            "%d unique contexts from %d samples", len(unique_contexts), len(samples),
        )

        # Attach gold point id to each sample for exact relevance matching
        for s in samples:
            s["gold_id"] = context_set[s["context"]]

        # Build embeddings conditionally based on mode flags
        embeddings = build_embeddings(settings) if use_dense else None
        sparse_embedding = build_sparse_embeddings(settings) if use_bm25 else None

        # 3. Index contexts
        logger.info("Indexing contexts into temp Qdrant...")
        await _index_contexts(
            unique_contexts, qdrant_url, embeddings, sparse_embedding,
            use_dense=use_dense, use_bm25=use_bm25,
        )

        logger.info(
            "Retrieving for %d questions (k=%d, reranking=%s, mode=%s)...",
            len(samples), k, settings.reranking_enabled, mode_label,
        )
        all_results = await _retrieve_all(
            samples, qdrant_url, settings, embeddings, sparse_embedding, k,
            concurrency=retrieval_concurrency,
        )

        # Apply reranking if enabled
        all_results = await _apply_reranking(
            samples, all_results, settings, concurrency=rerank_concurrency,
        )

        # 5-7. Compute metrics and save CSV
        df = _save_csv(samples, all_results, settings, k, mode=mode_label)

        # 8. Print summary
        _print_summary(df, len(samples), k)

    finally:
        _stop_qdrant_container(container_id)


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(evaluate_retrieval(
        k=args.k,
        size=args.size,
        retrieval_concurrency=args.retrieval_concurrency,
        rerank_concurrency=args.rerank_concurrency,
        use_dense=args.use_dense,
        use_bm25=args.use_bm25,
    ))
