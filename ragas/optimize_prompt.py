"""Optimize RAG system prompt by generating variants and evaluating with RAGAS metrics.

Generates N system prompt variants via LLM, evaluates each through the QAService
pipeline, scores with RAGAS metrics, and ranks to find the best performing prompt.

Usage:
    uv run python ragas/optimize_prompt.py
    uv run python ragas/optimize_prompt.py --variants 15 --sample-size 10
    uv run python ragas/optimize_prompt.py --base-prompt ragas/my_prompt.txt
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
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
    get_async_client,
    load_testset,
    resolve_llm_endpoint,
    score_with_metrics,
)
from openai import AsyncOpenAI
from ragas import EvaluationDataset

from cafetera_rag_service.config import RagServiceSettings
from cafetera_rag_service.resources import build_qa_service, close_rag_resources

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

_RESULTS_PATH = Path(__file__).parent / "optimization_results.json"
_BEST_PROMPT_PATH = Path(__file__).parent / "best_prompt.txt"

# ---------------------------------------------------------------------------
# Variation themes — used to nudge the LLM toward diverse prompt variants
# ---------------------------------------------------------------------------

_VARIATION_THEMES = [
    # Стиль и тон
    # "Make it more concise and direct",
    # "Prioritize user-friendliness and empathy",
    # "Make it more formal and professional",
    # "Use supportive professional tone without rigid or prohibitive language",

    # Цитирование и источники
    "Emphasize document citation and source attribution",
    "Use explicit source citation format for every factual claim",

    # Структура ответа
    "Focus on structured output formatting (lists, sections)",
    "Separate behavioral rules from formatting rules into two distinct blocks",
    "Start every response with a one-sentence direct answer before details",

    # Обработка edge-cases
    "Add explicit handling of ambiguous questions",
    "Focus on handling contradictions in sources",
    "Add explicit instructions for different question types",

    # Правила и точность
    "Make rules more explicit and numbered",
    "Emphasize accuracy over completeness",
    "Emphasize brevity in responses",
    "Place security and refusal rules at the end of the prompt",

    # Расширенные возможности
    "Add examples of expected behavior",
    "Add multilingual support: respond in the language of the user's question",
]

# ---------------------------------------------------------------------------
# Meta-prompt for variant generation
# ---------------------------------------------------------------------------

_META_PROMPT = """\
You are a prompt engineer. Your task is to write a system prompt for a \
Russian-language HR assistant chatbot that answers employee questions \
strictly from provided document context (RAG).

Here is the current system prompt used as a reference:

---
{base_prompt}
---

IMPORTANT: Previous experiments showed these patterns improve quality metrics:
- Starting response with a direct answer first improves context precision
- Explicit citation format «Согласно документу "[Название]"...» improves semantic similarity
- Separating formatting rules into a dedicated «Структура ответа» block improves all metrics
- Avoiding words like «строго», «запрещено» in the role definition improves answer relevancy
- Overly long meta-instructions (>600 chars of rules) reduce semantic similarity

Generate a CREATIVE VARIATION of this prompt. The variation MUST obey these \
CORE rules:
1. The assistant MUST answer ONLY from the provided context (grounding) — \
no hallucination, no general knowledge.
2. The assistant MUST refuse when context is insufficient.
3. The prompt MUST be written entirely in Russian.
4. The prompt MUST include the literal placeholder {{context}} where retrieved \
documents will be injected.

However, you SHOULD VARY the following aspects:
- Structure and ordering of instructions
- Tone (formal, friendly, strict, supportive)
- Formatting directives (lists, headings, bullet points)
- Emphasis and word choice
- Number and granularity of rules
- Specificity of instructions

Additional emphasis for this variation: {theme}

Output ONLY the system prompt text in Russian. No explanations, no markdown \
fences, no preamble — just the raw prompt text ready to be used as-is.
"""

# ---------------------------------------------------------------------------
# Variant generation
# ---------------------------------------------------------------------------


async def generate_variants(
    settings: RagServiceSettings,
    base_prompt: str,
    n: int,
) -> list[str]:
    """Generate N system prompt variants via the configured LLM.

    Uses the OpenAI-compatible chat completions API with high temperature
    for diversity.  Each variant gets a different 'theme' hint from
    ``_VARIATION_THEMES`` to encourage structural diversity.

    Returns a list of successfully generated prompt strings (may be < n
    if some generations fail).
    """
    base_url, api_key, provider = resolve_llm_endpoint(settings)
    client_cache: dict[tuple[str, str], AsyncOpenAI] = {}
    client = get_async_client(base_url, api_key, client_cache)

    # Build provider-specific extra_body for generation requests.
    extra_body: dict[str, Any] = {}
    if provider == "ollama":
        options: dict[str, Any] = {}
        if settings.llm_num_ctx:
            options["num_ctx"] = settings.llm_num_ctx
        options["num_predict"] = 4096
        extra_body = {"options": options}
    elif provider == "llamacpp":
        if settings.llm_num_ctx:
            extra_body["n_ctx"] = settings.llm_num_ctx
        extra_body["n_predict"] = 4096

    variants: list[str] = []

    for i in range(n):
        theme = _VARIATION_THEMES[i % len(_VARIATION_THEMES)]
        prompt_text = _META_PROMPT.format(base_prompt=base_prompt, theme=theme)

        logger.info(
            "Generating variant %d/%d (theme: %s)", i + 1, n, theme[:50],
        )

        try:
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=4096,
                temperature=0.9,
                extra_body=extra_body if extra_body else None,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                # Validate the variant contains {context} placeholder.
                if "{context}" in content:
                    variants.append(content.strip())
                    logger.info("Variant %d generated (%d chars)", i + 1, len(content))
                else:
                    logger.warning(
                        "Variant %d missing {context} placeholder, skipping", i + 1,
                    )
            else:
                logger.warning("Variant %d returned empty content, skipping", i + 1)
        except Exception:
            logger.exception("Failed to generate variant %d", i + 1)

    logger.info("Generated %d/%d variants successfully", len(variants), n)
    return variants


# ---------------------------------------------------------------------------
# Single variant evaluation
# ---------------------------------------------------------------------------


async def evaluate_variant(
    variant_idx: int,
    prompt_text: str,
    samples: list[dict[str, Any]],
    settings: RagServiceSettings,
    ragas_llm: Any,
    ragas_embeddings: Any,
    has_reference: bool,
) -> dict[str, Any]:
    """Evaluate a single prompt variant through QAService + RAGAS scoring.

    Builds fresh RAG resources, runs all samples through QAService with
    the given prompt, then scores with aevaluate().

    Returns a dict with variant metadata, per-sample scores, and aggregates.
    """
    label = f"var_{variant_idx:02d}" if variant_idx > 0 else "base"
    logger.info("=" * 60)
    logger.info("Evaluating variant: %s", label)
    logger.info("=" * 60)

    res = await build_ragas_resources(settings)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_QA)

    try:
        qa = build_qa_service(res, prompt_text, include_metadata=True)

        # Phase 1: Run QA on all samples.
        async def _ask(sample: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                question = sample.get("user_input", "")
                if not question:
                    return {**sample, "response": "", "retrieved_contexts": []}

                logger.info("[%s] Asking: %s", label, question[:80])
                try:
                    answer, contexts = await qa.ask_with_contexts(question)
                except Exception:
                    logger.exception(
                        "[%s] Failed on question: %s", label, question[:80],
                    )
                    answer, contexts = "", []

                return {
                    **sample,
                    "response": answer,
                    "retrieved_contexts": contexts,
                }

        collected = await asyncio.gather(*[_ask(s) for s in samples])

        # Phase 2: Score with RAGAS ``aevaluate()`` via the shared helper.
        # Metric composition is owned by ``build_eval_metrics()`` in
        # ``_common.py`` and shared with ``evaluate.py``.
        #
        # Conditional metric wiring for prompt optimization:
        #
        # - ``has_reference_contexts`` is intentionally NOT forwarded:
        #   retrieval in ``ask_with_contexts()`` depends only on
        #   ``(question, category, k)`` — the system prompt has no influence.
        #   ``NonLLMContextRecall`` would therefore return the same score for
        #   every variant (a constant) and only dilute the overall_avg spread
        #   used for ranking.
        #
        # - ``has_reference`` is forwarded when the testset provides ground
        #   truth: ``SemanticSimilarity`` compares the response embedding to
        #   the reference embedding, which DOES depend on the system prompt.
        #   It is fully deterministic (no LLM), cheap (one embedding per
        #   sample), and adds a noise-free ranking signal — critical when the
        #   evaluator LLM is a small local model with noisy verdicts.
        metrics: list[Any] = build_eval_metrics(
            ragas_llm,
            ragas_embeddings,
            has_reference=has_reference,
        )

        eval_dataset = EvaluationDataset.from_list(list(collected))

        result = await score_with_metrics(eval_dataset, metrics)

        # Extract scores.
        scores = result.scores
        metric_names = sorted(
            k for k in scores[0] if isinstance(scores[0][k], (int, float))
        ) if scores else []

        # Compute averages.
        averages: dict[str, float] = {}
        for metric in metric_names:
            values = [
                s[metric] for s in scores
                if s.get(metric) is not None and not _is_nan(s[metric])
            ]
            averages[metric] = sum(values) / len(values) if values else float("nan")

        overall_avg = (
            sum(v for v in averages.values() if not _is_nan(v))
            / sum(1 for v in averages.values() if not _is_nan(v))
            if any(not _is_nan(v) for v in averages.values())
            else float("nan")
        )

        return {
            "variant_idx": variant_idx,
            "label": label,
            "prompt_text": prompt_text,
            "scores": scores,
            "averages": averages,
            "overall_avg": overall_avg,
        }

    except Exception:
        logger.exception("Evaluation failed for variant %s", label)
        return {
            "variant_idx": variant_idx,
            "label": label,
            "prompt_text": prompt_text,
            "scores": [],
            "averages": {},
            "overall_avg": float("nan"),
        }
    finally:
        await close_rag_resources(res)


def _is_nan(value: float) -> bool:
    """Check if a float value is NaN."""
    return value != value  # noqa: PLR0124


# ---------------------------------------------------------------------------
# Results output
# ---------------------------------------------------------------------------


def _print_comparison_table(results: list[dict[str, Any]]) -> None:
    """Print ranked comparison table of all variants."""
    # Sort by overall_avg descending (NaN last).
    ranked = sorted(
        results,
        key=lambda r: r["overall_avg"] if not _is_nan(r["overall_avg"]) else -1,
        reverse=True,
    )

    # Collect all metric names across results.
    all_metrics: set[str] = set()
    for r in ranked:
        all_metrics.update(r.get("averages", {}).keys())
    metric_cols = sorted(all_metrics)

    print("\n" + "=" * 80)
    print("PROMPT OPTIMIZATION RESULTS (ranked by avg score)")
    print("=" * 80)

    # Header.
    header = f"  {'#':>3}  {'Variant':<10}"
    for m in metric_cols:
        short = m[:14]
        header += f"  {short:<14}"
    header += f"  {'Avg Score':<10}"
    print(header)
    print("-" * 80)

    # Rows.
    for rank, r in enumerate(ranked, 1):
        row = f"  {rank:>3}  {r['label']:<10}"
        for m in metric_cols:
            val = r.get("averages", {}).get(m, float("nan"))
            row += f"  {val:<14.3f}" if not _is_nan(val) else f"  {'N/A':<14}"
        avg = r["overall_avg"]
        row += f"  {avg:<10.3f}" if not _is_nan(avg) else f"  {'N/A':<10}"
        print(row)

    print("=" * 80)


def _save_intermediate(results: list[dict[str, Any]], path: Path) -> None:
    """Save current results to JSON for resumability."""
    # Convert NaN to None for JSON serialization.
    serializable = []
    for r in results:
        entry = {
            "variant_idx": r["variant_idx"],
            "label": r["label"],
            "prompt_text": r["prompt_text"],
            "averages": {
                k: v if not _is_nan(v) else None
                for k, v in r.get("averages", {}).items()
            },
            "overall_avg": (
                r["overall_avg"] if not _is_nan(r["overall_avg"]) else None
            ),
        }
        serializable.append(entry)

    path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Intermediate results saved to %s", path)


# ---------------------------------------------------------------------------
# Main optimization loop
# ---------------------------------------------------------------------------


async def run_optimization(
    testset_path: Path,
    *,
    num_variants: int = 10,
    sample_size: int = 0,
    base_prompt_path: Path | None = None,
    name_override: str | None = None,
) -> None:
    """Run prompt optimization: generate variants, evaluate, rank.

    Phase 1: Generate N system prompt variants via LLM.
    Phase 2: Evaluate baseline + all variants with RAGAS metrics.
    Phase 3: Rank and output results.
    """
    settings = RagServiceSettings()

    # 1. Load base prompt.
    if base_prompt_path and base_prompt_path.exists():
        base_prompt = base_prompt_path.read_text(encoding="utf-8").strip()
        logger.info("Loaded base prompt from %s", base_prompt_path)
    else:
        base_prompt = EVAL_SYSTEM_PROMPT
        logger.info("Using default EVAL_SYSTEM_PROMPT as base")

    # 2. Load and optionally subsample testset.
    samples = load_testset(testset_path)
    logger.info("Loaded %d samples from %s", len(samples), testset_path)

    if sample_size > 0 and sample_size < len(samples):
        random.seed(42)
        samples = random.sample(samples, sample_size)
        logger.info("Subsampled to %d samples (seed=42)", sample_size)

    has_reference = all("reference" in s and s["reference"] for s in samples)

    # 3. Build scorer LLM + embeddings for RAGAS metrics.
    client_cache: dict[tuple[str, str], AsyncOpenAI] = {}
    ragas_llm = build_ragas_llm(
        settings, client_cache, max_tokens=EVALUATOR_MAX_TOKENS,
    )
    ragas_embeddings = build_ragas_embeddings(
        settings, client_cache, interface="legacy",
    )

    # 4. Phase 1 — Generate variants.
    logger.info("=" * 60)
    logger.info("PHASE 1: Generating %d prompt variants", num_variants)
    logger.info("=" * 60)

    variants = await generate_variants(settings, base_prompt, num_variants)

    if not variants:
        logger.error("No variants generated. Check LLM connectivity.")
        return

    # 5. Phase 2 — Evaluate baseline + variants.
    logger.info("=" * 60)
    logger.info(
        "PHASE 2: Evaluating %d variants (baseline + %d generated)",
        len(variants) + 1,
        len(variants),
    )
    logger.info("=" * 60)

    all_results: list[dict[str, Any]] = []

    # Evaluate baseline first (variant #0).
    baseline_result = await evaluate_variant(
        variant_idx=0,
        prompt_text=base_prompt,
        samples=samples,
        settings=settings,
        ragas_llm=ragas_llm,
        ragas_embeddings=ragas_embeddings,
        has_reference=has_reference,
    )
    all_results.append(baseline_result)
    _save_intermediate(all_results, _RESULTS_PATH)

    # Evaluate each generated variant.
    for i, variant_prompt in enumerate(variants, 1):
        variant_result = await evaluate_variant(
            variant_idx=i,
            prompt_text=variant_prompt,
            samples=samples,
            settings=settings,
            ragas_llm=ragas_llm,
            ragas_embeddings=ragas_embeddings,
            has_reference=has_reference,
        )
        all_results.append(variant_result)
        _save_intermediate(all_results, _RESULTS_PATH)

    # 6. Phase 3 — Rank and output.
    logger.info("=" * 60)
    logger.info("PHASE 3: Results")
    logger.info("=" * 60)

    _print_comparison_table(all_results)

    # Find best variant.
    valid_results = [
        r for r in all_results if not _is_nan(r["overall_avg"])
    ]
    if valid_results:
        best = max(valid_results, key=lambda r: r["overall_avg"])
        _BEST_PROMPT_PATH.write_text(best["prompt_text"], encoding="utf-8")
        print(f"\nBest prompt saved to: {_BEST_PROMPT_PATH}")
        print(f"Best variant: {best['label']} (avg score: {best['overall_avg']:.3f})")
    else:
        logger.warning("No valid results — cannot determine best prompt")

    logger.info("Final results saved to %s", _RESULTS_PATH)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optimize RAG system prompt via LLM-generated variants",
    )
    parser.add_argument(
        "--variants",
        type=int,
        default=10,
        help="Number of prompt variants to generate (default: 10)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=0,
        help="Subsample testset to N items; 0 = use all (default: 0)",
    )
    parser.add_argument(
        "--testset",
        type=Path,
        default=DEFAULT_TESTSET,
        help=f"Path to testset JSON (default: {DEFAULT_TESTSET})",
    )
    parser.add_argument(
        "--base-prompt",
        type=Path,
        default=None,
        help="Path to base prompt text file (default: built-in EVAL_SYSTEM_PROMPT)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Override run name (used in output logging)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        run_optimization(
            testset_path=args.testset,
            num_variants=args.variants,
            sample_size=args.sample_size,
            base_prompt_path=args.base_prompt,
            name_override=args.name,
        )
    )
