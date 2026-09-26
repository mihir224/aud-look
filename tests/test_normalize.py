import pytest

from app.ingestion.normalize import normalize_text, validate_words, words_to_utterances
from app.schemas import Word


def words() -> list[Word]:
    return [
        Word("Hello", "spk_1", 0, 400),
        Word("there.", "spk_1", 500, 800),
        Word("Hi!", "spk_2", 1000, 1200),
        Word("How", "spk_2", 1300, 1500),
        Word("are", "spk_2", 1600, 1800),
        Word("you?", "spk_2", 1900, 2200),
    ]


def test_words_become_speaker_attributed_utterances():
    utterances = words_to_utterances(words())
    assert [(item.speaker, item.text) for item in utterances] == [
        ("spk_1", "Hello there."),
        ("spk_2", "Hi! How are you?"),
    ]


def test_validation_requires_two_monotonic_speakers():
    validate_words(words(), 3_000)
    with pytest.raises(ValueError, match="exactly two speakers"):
        validate_words([Word("only", "spk_1", 0, 1)], 3_000)
    # Speaker overlap is valid cross-talk.
    validate_words([Word("a", "spk_1", 100, 200), Word("b", "spk_2", 150, 220)], 3_000)
    with pytest.raises(ValueError, match="not monotonic"):
        validate_words([Word("a", "spk_1", 200, 250), Word("b", "spk_2", 150, 220)], 3_000)


def test_normalization_is_stable():
    assert normalize_text("  Basecamp   VC ") == "basecamp vc"
