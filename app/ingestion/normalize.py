import re

from app.schemas import Utterance, Word


SENTENCE_END = re.compile(r"[.!?][\"')\]]*$")


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def validate_words(words: list[Word], duration_ms: int) -> None:
    if not words:
        raise ValueError("Transcript contains no words")
    speakers = {word.speaker for word in words if word.speaker}
    if len(speakers) != 2:
        raise ValueError(f"Expected exactly two speakers, found {sorted(speakers)}")
    previous_start = 0
    for word in words:
        if not word.text.strip():
            raise ValueError("Transcript contains an empty word")
        # Cross-talk can make word intervals overlap. The canonical transcript is
        # sorted by start time, so only a time reversal—not an overlap—is invalid.
        if word.start_ms < previous_start or word.end_ms < word.start_ms:
            raise ValueError("Word timestamps are not monotonic")
        if word.end_ms > duration_ms + 1000:
            raise ValueError("Word timestamp exceeds source duration")
        previous_start = word.start_ms


def words_to_utterances(words: list[Word]) -> list[Utterance]:
    """Create speaker-attributed, bounded utterances without splitting a word."""
    utterances: list[Utterance] = []
    current: list[Word] = []

    def flush() -> None:
        if not current:
            return
        utterances.append(
            Utterance(
                sequence_no=len(utterances) + 1,
                speaker=current[0].speaker,
                start_ms=current[0].start_ms,
                end_ms=current[-1].end_ms,
                text=" ".join(word.text for word in current).strip(),
            )
        )
        current.clear()

    for word in words:
        if current and word.speaker != current[0].speaker:
            flush()
        current.append(word)
        elapsed = current[-1].end_ms - current[0].start_ms
        is_sentence_boundary = bool(SENTENCE_END.search(word.text))
        if elapsed >= 45_000 or len(current) >= 80 or (elapsed >= 5_000 and is_sentence_boundary):
            flush()
    flush()
    return utterances
