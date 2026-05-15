"""Markdown → vkbottle Format converter for VK Messenger.

Uses *mistune* to parse Markdown into an AST and walks the tree to build
vkbottle ``Format`` objects with offset-based rich formatting (bold, italic,
underline, hyperlinks).

VK Messenger does **not** support HTML in messages — it uses its own
``format_data`` parameter with offset/length pairs.  The helpers from
``vkbottle.tools.formatting`` produce the correct ``Format`` objects.
"""

from __future__ import annotations

import logging

import mistune
from vkbottle.tools.formatting import Format, bold, italic, underline  # noqa: F401
from vkbottle.tools.formatting import url as vk_url

logger = logging.getLogger(__name__)

# Internal union: intermediate results are either plain str or Format.
_Chunk = str | Format


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merge_chunks(chunks: list[_Chunk]) -> _Chunk:
    """Concatenate a list of ``str | Format`` chunks into a single value.

    Uses the ``+`` operator which vkbottle Format supports for both
    ``str`` and ``Format`` right-hand operands.
    """
    if not chunks:
        return ""
    result: _Chunk = chunks[0]
    for chunk in chunks[1:]:
        if not chunk:  # skip empty strings
            continue
        result = result + chunk
    return result


def _ensure_format(chunk: _Chunk) -> Format:
    """Guarantee the result is a ``Format`` object.

    If *chunk* is a plain ``str``, wraps it by prepending a zero-length
    ``bold("")`` so that the type is ``Format`` (VK ignores the empty item).
    """
    if isinstance(chunk, Format):
        return chunk
    return bold("") + chunk


def _plain_text(token: dict) -> str:
    """Recursively extract plain text from a token, ignoring all formatting."""
    if token.get("type") == "text":
        return token.get("raw", "")
    if token.get("type") == "codespan":
        return token.get("raw", "")
    children = token.get("children", [])
    return "".join(_plain_text(c) for c in children)


def _plain_text_many(children: list[dict]) -> str:
    return "".join(_plain_text(c) for c in children)


# ---------------------------------------------------------------------------
# Inline AST walkers
# ---------------------------------------------------------------------------


def _walk_inline(children: list[dict]) -> list[_Chunk]:
    """Walk inline-level AST nodes and produce ``str | Format`` chunks."""
    chunks: list[_Chunk] = []
    for token in children:
        ttype = token.get("type", "")

        if ttype == "text":
            raw = token.get("raw", "")
            if raw:
                chunks.append(raw)

        elif ttype == "strong":
            inner_chunks = _walk_inline(token.get("children", []))
            inner = _merge_chunks(inner_chunks) if inner_chunks else ""
            if inner:
                chunks.append(bold(inner))

        elif ttype == "emphasis":
            inner_chunks = _walk_inline(token.get("children", []))
            inner = _merge_chunks(inner_chunks) if inner_chunks else ""
            if inner:
                chunks.append(italic(inner))

        elif ttype == "codespan":
            raw = token.get("raw", "")
            if raw:
                chunks.append(raw)

        elif ttype == "link":
            inner_chunks = _walk_inline(token.get("children", []))
            inner = _merge_chunks(inner_chunks) if inner_chunks else ""
            href = token.get("attrs", {}).get("url", "")
            if href and inner:
                chunks.append(vk_url(inner, href=href))
            elif href:
                chunks.append(vk_url(href, href=href))
            elif inner:
                chunks.append(inner)

        elif ttype in ("softbreak", "linebreak"):
            chunks.append("\n")

        elif ttype == "strikethrough":
            inner = _plain_text_many(token.get("children", []))
            if inner:
                chunks.append(inner)

        else:
            # Unknown inline — best-effort plain text extraction.
            text = _plain_text(token)
            if text:
                chunks.append(text)

    return chunks


# ---------------------------------------------------------------------------
# Block AST walker
# ---------------------------------------------------------------------------


def _walk_blocks(tokens: list[dict]) -> list[_Chunk]:
    """Walk block-level AST and produce ``str | Format`` chunks."""
    chunks: list[_Chunk] = []
    need_sep = False  # whether to prepend \n\n before next visible block

    for token in tokens:
        ttype = token.get("type", "")

        if ttype == "blank_line":
            continue

        # ── paragraph ───────────────────────────────────────────────
        if ttype == "paragraph":
            if need_sep:
                chunks.append("\n\n")
            chunks.extend(_walk_inline(token.get("children", [])))
            need_sep = True

        # ── heading → bold ──────────────────────────────────────────
        elif ttype == "heading":
            if need_sep:
                chunks.append("\n\n")
            text = _plain_text_many(token.get("children", []))
            if text:
                chunks.append(bold(text))
            need_sep = True

        # ── unordered / ordered list ────────────────────────────────
        elif ttype == "list":
            if need_sep:
                chunks.append("\n\n")
            attrs = token.get("attrs", {})
            ordered = attrs.get("ordered", False)

            for idx, item in enumerate(token.get("children", [])):
                if idx > 0:
                    chunks.append("\n")
                prefix = f"{idx + 1}. " if ordered else "• "
                chunks.append(prefix)

                for block in item.get("children", []):
                    btype = block.get("type", "")
                    if btype in ("block_text", "paragraph"):
                        chunks.extend(_walk_inline(block.get("children", [])))
                    else:
                        text = _plain_text(block)
                        if text:
                            chunks.append(text)
            need_sep = True

        # ── fenced / indented code block ────────────────────────────
        elif ttype == "block_code":
            if need_sep:
                chunks.append("\n\n")
            raw = token.get("raw", "").rstrip("\n")
            if raw:
                chunks.append(raw)
            need_sep = True

        # ── thematic break (---) → em-dash line ────────────────────
        elif ttype == "thematic_break":
            if need_sep:
                chunks.append("\n\n")
            chunks.append("———")
            need_sep = True

        # ── block_text (direct child in some structures) ────────────
        elif ttype == "block_text":
            if need_sep:
                chunks.append("\n\n")
            chunks.extend(_walk_inline(token.get("children", [])))
            need_sep = True

        # ── unknown block → plain text ──────────────────────────────
        else:
            text = _plain_text(token)
            if text:
                if need_sep:
                    chunks.append("\n\n")
                chunks.append(text)
                need_sep = True

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def markdown_to_format(text: str) -> Format:
    """Convert Markdown *text* to a vkbottle ``Format`` with rich formatting.

    Uses mistune to parse Markdown into an AST, then walks the tree to build
    offset-based VK formatting via ``vkbottle.tools.formatting`` helpers
    (bold, italic, underline, url).

    Falls back to the original text as a plain ``Format`` if parsing fails.
    """
    if not text or not text.strip():
        return _ensure_format(text or "")

    try:
        md = mistune.create_markdown(renderer="ast", plugins=["strikethrough"])
        tokens: list[dict] = md(text)  # type: ignore[assignment]
        chunks = _walk_blocks(tokens)
        if not chunks:
            return _ensure_format(text)
        merged = _merge_chunks(chunks)
        return _ensure_format(merged)
    except Exception:
        logger.warning("Failed to parse markdown, returning plain text", exc_info=True)
        return _ensure_format(text)
