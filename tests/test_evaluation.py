from app.evaluation import overlaps


def test_temporal_relevance_requires_same_episode_and_major_overlap():
    result = {"audio_slug": "episode-a", "start_ms": 1_000, "end_ms": 5_000}
    assert overlaps(result, {"audio_slug": "episode-a", "start_ms": 2_000, "end_ms": 4_000})
    assert not overlaps(result, {"audio_slug": "episode-b", "start_ms": 2_000, "end_ms": 4_000})
    assert not overlaps(result, {"audio_slug": "episode-a", "start_ms": 4_900, "end_ms": 8_000})

