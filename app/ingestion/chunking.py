from app.schemas import Chunk, Utterance


def render_chunk(utterances: list[Utterance]) -> str:
    return "\n".join(f"{utterance.speaker}: {utterance.text}" for utterance in utterances)


def build_chunks(utterances: list[Utterance]) -> list[Chunk]:
    """Build 100–160 word, 30–50 second conversational chunks with one-turn overlap."""
    if not utterances:
        return []
    raw_chunks: list[list[Utterance]] = []
    start_index = 0
    while start_index < len(utterances):
        selected: list[Utterance] = []
        word_count = 0
        for utterance in utterances[start_index:]:
            next_words = len(utterance.text.split())
            elapsed = utterance.end_ms - (selected[0].start_ms if selected else utterance.start_ms)
            if selected and (word_count + next_words > 160 or elapsed > 50_000):
                break
            selected.append(utterance)
            word_count += next_words
            elapsed = selected[-1].end_ms - selected[0].start_ms
            if word_count >= 100 or elapsed >= 30_000:
                break
        if not selected:
            selected = [utterances[start_index]]
        raw_chunks.append(selected)
        if selected[-1].sequence_no == utterances[-1].sequence_no:
            break
        start_index = max(start_index + 1, utterances.index(selected[-1]))

    if len(raw_chunks) > 1:
        last = raw_chunks[-1]
        last_words = sum(len(item.text.split()) for item in last)
        last_duration = last[-1].end_ms - last[0].start_ms
        if last_words < 50 and last_duration < 15_000:
            previous = raw_chunks[-2]
            merged = previous + [item for item in last if item.sequence_no > previous[-1].sequence_no]
            raw_chunks[-2] = merged
            raw_chunks.pop()

    return [
        Chunk(
            start_ms=items[0].start_ms,
            end_ms=items[-1].end_ms,
            text=render_chunk(items),
            utterance_sequence_nos=[item.sequence_no for item in items],
        )
        for items in raw_chunks
    ]

