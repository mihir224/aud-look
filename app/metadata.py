import re
from functools import lru_cache
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEAKER_NAMES_PATH = PROJECT_ROOT / "dataset" / "speaker_names.yaml"
ENTITY_ALIASES_PATH = PROJECT_ROOT / "dataset" / "entity_aliases.yaml"


@lru_cache
def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def speaker_identity(audio_slug: str, speaker: str) -> dict[str, str]:
    """Return presentation metadata while preserving the diarization label."""
    identity = _load_yaml(SPEAKER_NAMES_PATH).get(audio_slug, {}).get(speaker, {})
    return {
        "name": identity.get("name", speaker),
        "role": identity.get("role", "speaker"),
    }


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase.strip()).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def expand_entity_query(query: str) -> list[str]:
    """Create lexical query variants for reviewed entity spellings.

    Only the query changes. Canonical transcript text and returned evidence stay verbatim.
    """
    variants = [query]
    for group in _load_yaml(ENTITY_ALIASES_PATH).get("aliases", []):
        equivalents = [group["canonical"], *group.get("variants", [])]
        for source in equivalents:
            pattern = _phrase_pattern(source)
            if not pattern.search(query):
                continue
            variants.extend(pattern.sub(target, query) for target in equivalents if target.lower() != source.lower())
            break
    return list(dict.fromkeys(variant.lower() for variant in variants))
