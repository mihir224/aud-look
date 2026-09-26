from app.ingestion.chunking import build_chunks
from app.schemas import Utterance


def test_chunks_have_one_utterance_overlap():
    utterances = [
        Utterance(index, "spk_1" if index % 2 else "spk_2", (index - 1) * 10_000, index * 10_000, "word " * 40)
        for index in range(1, 6)
    ]
    chunks = build_chunks(utterances)
    assert len(chunks) >= 2
    assert chunks[0].utterance_sequence_nos[-1] == chunks[1].utterance_sequence_nos[0]
    assert all("spk_" in chunk.text for chunk in chunks)


def test_chunk_does_not_split_utterance():
    utterances = [Utterance(1, "spk_1", 0, 60_000, "word " * 170)]
    chunks = build_chunks(utterances)
    assert chunks[0].utterance_sequence_nos == [1]

