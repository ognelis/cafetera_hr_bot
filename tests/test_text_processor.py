"""Tests for Russian text preprocessing (lemmatization + stop-word removal)."""

from cafetera_rag_service.rag.text_processor import RUSSIAN_STOP_WORDS, preprocess_russian

# -- Basic lemmatization -------------------------------------------------------


def test_lemmatize_noun_plural():
    """Plural noun "машины" should lemmatize to "машина"."""
    assert preprocess_russian("машины") == "машина"


def test_lemmatize_verb_past():
    """Past-tense verb "играли" should lemmatize to "играть"."""
    assert preprocess_russian("играли") == "играть"


def test_lemmatize_ambiguous_myla():
    """pymorphy3 resolves "мыла" to noun "мыло" (soap) as most probable."""
    assert preprocess_russian("мыла") == "мыло"


# -- Stop word removal ---------------------------------------------------------


def test_stop_words_removed():
    """Common stop words should be removed entirely."""
    for word in ("в", "на", "и", "но", "а"):
        assert word in RUSSIAN_STOP_WORDS
        assert preprocess_russian(word) == ""


def test_stop_word_set_is_frozenset():
    assert isinstance(RUSSIAN_STOP_WORDS, frozenset)
    assert len(RUSSIAN_STOP_WORDS) > 100


# -- Combined ------------------------------------------------------------------


def test_combined_sentence():
    """Full sentence: lemmatize + remove stop words."""
    result = preprocess_russian("Мама мыла раму, а дети играли дома")
    assert result == "мама мыло рама ребёнок играть дом"


# -- Punctuation ---------------------------------------------------------------


def test_punctuation_stripped():
    """Commas, periods, exclamation marks should not appear in output."""
    result = preprocess_russian("Привет! Как дела? Хорошо, спасибо.")
    assert "!" not in result
    assert "?" not in result
    assert "," not in result
    assert "." not in result


def test_punctuation_does_not_split_words():
    result = preprocess_russian("кот, собака")
    assert "кот" in result
    assert "собака" in result


# -- Empty input ---------------------------------------------------------------


def test_empty_string():
    assert preprocess_russian("") == ""


def test_none_like_empty():
    """Empty-ish whitespace should produce empty output."""
    assert preprocess_russian("   ") == ""


# -- Mixed Russian / English ---------------------------------------------------


def test_mixed_russian_english_no_crash():
    """English tokens should pass through without errors."""
    result = preprocess_russian("Python отлично работает")
    assert "python" in result
    assert "работать" in result


def test_pure_english():
    result = preprocess_russian("hello world")
    assert "hello" in result
    assert "world" in result


# -- Idempotency ---------------------------------------------------------------


def test_idempotency():
    """Preprocessing already-lemmatized text produces the same output."""
    first = preprocess_russian("Мама мыла раму, а дети играли дома")
    second = preprocess_russian(first)
    assert first == second


# -- Only stop words -----------------------------------------------------------


def test_only_stop_words():
    """Input consisting entirely of stop words returns empty string."""
    assert preprocess_russian("в на и но а") == ""


def test_only_stop_words_with_punctuation():
    assert preprocess_russian("в, на; и — но!") == ""


# -- Numbers -------------------------------------------------------------------


def test_numbers_pass_through():
    """Numeric tokens should survive preprocessing."""
    result = preprocess_russian("офис 42 этаж 3")
    assert "42" in result
    assert "3" in result


def test_mixed_numbers_and_words():
    result = preprocess_russian("Документ 15 от января")
    assert "15" in result
    assert "документ" in result
