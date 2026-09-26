from types import SimpleNamespace

from app.transcription.gemini import extract_words


def test_extracts_word_annotations_from_gemini_response_shape():
    word = SimpleNamespace(word="Hello", start_offset="0.1s", end_offset="0.5s")
    transcription = SimpleNamespace(speaker_label="spk_1", words=[word])
    response = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(audio_transcription=transcription)]))])
    assert extract_words(response)[0].text == "Hello"
    assert extract_words(response)[0].start_ms == 100


def test_extracts_word_annotations_from_interactions_response_shape():
    annotation = SimpleNamespace(type="word_info", text="Hello", speaker="spk_1", start_offset="0.1s", end_offset="0.5s")
    response = SimpleNamespace(steps=[SimpleNamespace(content=[SimpleNamespace(annotations=[annotation])])])
    words = extract_words(response)
    assert len(words) == 1
    assert words[0].speaker == "spk_1"
