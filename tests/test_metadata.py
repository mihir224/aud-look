from app import metadata
from app.metadata import expand_entity_query, speaker_identity


def test_speaker_identity_is_presentation_metadata():
    assert speaker_identity("geoffrey-kent", "spk:1") == {"name": "Geoffrey Kent", "role": "guest"}
    assert speaker_identity("unknown", "spk:7") == {"name": "spk:7", "role": "speaker"}


def test_every_episode_has_reviewed_host_and_guest_mappings():
    slugs = {
        "janice-bryant-howroyd",
        "jason-fried",
        "manfredi-lefebvre-dovidio",
        "jordan-noone",
        "geoffrey-kent",
        "shaahin-cheyne",
    }
    for slug in slugs:
        host = speaker_identity(slug, "spk:0")
        guest = speaker_identity(slug, "spk:1")
        assert host == {"name": "Chris Reynolds", "role": "host"}
        assert guest["name"] != "spk:1"
        assert guest["role"] == "guest"


def test_entity_aliases_expand_names_without_changing_original_query():
    variants = expand_entity_query("what did Geoffrey Kent say about instinct")
    assert variants[0] == "what did geoffrey kent say about instinct"
    assert "what did jeffrey kent say about instinct" in variants


def test_entity_aliases_expand_transcription_variant_to_canonical_name():
    variants = expand_entity_query("Shaheen Shayan Amazon")
    assert "shaahin cheyene amazon" in variants


def test_metadata_paths_do_not_depend_on_current_working_directory(monkeypatch, tmp_path):
    metadata._load_yaml.cache_clear()
    monkeypatch.chdir(tmp_path)
    assert speaker_identity("jordan-noone", "spk:1")["name"] == "Jordan Noone"
    assert "jeffrey kent" in expand_entity_query("Geoffrey Kent")
