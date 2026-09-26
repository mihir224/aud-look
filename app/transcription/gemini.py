import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from google import genai

from app.config import Settings
from app.schemas import Word


MODEL = "gemini-3.5-transcribe"
CONFIG = {
    "language_codes": ["en"],
    "mode": {
        "type": "verbatim",
        "diarization_mode": "speaker",
        "timestamp_granularities": ["word"],
    },
}


def transcription_config_hash(audio_sha256: str) -> str:
    payload = json.dumps({"audio_sha256": audio_sha256, "model": MODEL, "config": CONFIG}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _value(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _milliseconds(value: Any) -> int:
    if isinstance(value, (int, float)):
        return round(float(value) * 1000)
    text = str(value or "0s")
    if text.endswith("s"):
        text = text[:-1]
    return round(float(text) * 1000)


def extract_words(response: Any) -> list[Word]:
    words: list[Word] = []
    # Gemini 3.5 Transcribe returns word annotations from Interactions API.
    # Keep the candidate/part fallback for cached responses from the legacy API.
    for step in _value(response, "steps", []) or []:
        for content in _value(step, "content", []) or []:
            for annotation in _value(content, "annotations", []) or []:
                if _value(annotation, "type") != "word_info":
                    continue
                words.append(
                    Word(
                        text=str(_value(annotation, "text", "")).strip(),
                        speaker=str(_value(annotation, "speaker", "unknown")),
                        start_ms=_milliseconds(_value(annotation, "start_offset")),
                        end_ms=_milliseconds(_value(annotation, "end_offset")),
                    )
                )
    if words:
        return words
    for candidate in _value(response, "candidates", []) or []:
        content = _value(candidate, "content")
        for part in _value(content, "parts", []) or []:
            transcription = _value(part, "audio_transcription")
            if transcription is None:
                continue
            speaker = _value(transcription, "speaker_label", "unknown")
            for word in _value(transcription, "words", []) or []:
                text = _value(word, "word", _value(word, "text", ""))
                words.append(
                    Word(
                        text=str(text).strip(),
                        speaker=str(speaker),
                        start_ms=_milliseconds(_value(word, "start_offset")),
                        end_ms=_milliseconds(_value(word, "end_offset")),
                    )
                )
    return words


class GeminiTranscriber:
    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for transcription; cached transcripts can be ingested without it.")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def transcribe(self, audio_path: Path) -> list[Word]:
        uploaded = None
        try:
            # The Gemini Files SDK includes the local filename in an ASCII HTTP
            # header. The supplied podcast names contain an em dash, so upload a
            # short ASCII copy without changing the source filename or manifest.
            with tempfile.TemporaryDirectory(prefix="aud-look-") as directory:
                upload_path = Path(directory) / "episode.mp3"
                shutil.copy2(audio_path, upload_path)
                uploaded = self.client.files.upload(file=str(upload_path))
            response = self.client.interactions.create(
                model=MODEL,
                input=[{"type": "audio", "uri": uploaded.uri, "mime_type": uploaded.mime_type}],
                generation_config={"transcription_config": CONFIG},
            )
            words = sorted(extract_words(response), key=lambda word: (word.start_ms, word.end_ms, word.speaker))
            if not words:
                raise RuntimeError("Gemini returned no timestamped transcription words")
            return words
        finally:
            if uploaded is not None:
                try:
                    self.client.files.delete(name=uploaded.name)
                except Exception:
                    # Avoid hiding a successful transcription because temporary cleanup failed.
                    pass
