"""Russian text preprocessing for BM25 sparse search.

Provides lemmatization and stop-word removal so that morphological
variants (e.g. "машина" / "машины") map to the same BM25 token.
"""

from __future__ import annotations

import re

import pymorphy3  # type: ignore[import-untyped]

_morph = pymorphy3.MorphAnalyzer()

# Official Russian stop words from Qdrant/bm25 model
# Source: https://huggingface.co/Qdrant/bm25/resolve/main/russian.txt
RUSSIAN_STOP_WORDS: frozenset[str] = frozenset({
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со",
    "как", "а", "то", "все", "она", "так", "его", "но", "да", "ты",
    "к", "у", "же", "вы", "за", "бы", "по", "только", "ее", "мне",
    "было", "вот", "от", "меня", "еще", "нет", "о", "из", "ему",
    "теперь", "когда", "даже", "ну", "вдруг", "ли", "если", "уже",
    "или", "ни", "быть", "был", "него", "до", "вас", "нибудь",
    "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего",
    "ей", "может", "они", "тут", "где", "есть", "надо", "ней", "для",
    "мы", "тебя", "их", "чем", "была", "сам", "чтоб", "без", "будто",
    "чего", "раз", "тоже", "себе", "под", "будет", "ж", "тогда",
    "кто", "этот", "того", "потому", "этого", "какой", "совсем",
    "ним", "здесь", "этом", "один", "почти", "мой", "тем", "чтобы",
    "нее", "сейчас", "были", "куда", "зачем", "всех", "никогда",
    "можно", "при", "наконец", "два", "об", "другой", "хоть", "после",
    "над", "больше", "тот", "через", "эти", "нас", "про", "всего",
    "них", "какая", "много", "разве", "три", "эту", "моя", "впрочем",
    "хорошо", "свою", "этой", "перед", "иногда", "лучше", "чуть",
    "том", "нельзя", "такой", "им", "более", "всегда", "конечно",
    "всю", "между",
})

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def preprocess_russian(text: str) -> str:
    """Lemmatize Russian text and remove stop words for BM25.

    Steps:
    1. Lowercase
    2. Strip punctuation
    3. Lemmatize every token with pymorphy3
    4. Drop stop words

    The same function MUST be applied at both index time and query time
    to keep sparse vectors consistent.
    """
    if not text:
        return ""
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    words = text.split()
    lemmas = [
        lemma
        for w in words
        if (lemma := _morph.parse(w)[0].normal_form) not in RUSSIAN_STOP_WORDS
    ]
    return " ".join(lemmas)
