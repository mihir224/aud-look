from app.retrieval.common import Candidate, canonical_query, deduplicate, literal_pattern, rrf_score
from app.retrieval.hybrid import _answer_pair_passage, _is_strict_literal_query, _looks_like_question


def test_canonical_query_and_literal_patterns():
    assert canonical_query('  "Basecamp VC" ') == "basecamp vc"
    assert literal_pattern("VC") == r"\mvc\M"
    assert literal_pattern("C++") == "c\\+\\+"


def test_deduplication_preserves_best_provenance():
    lexical = Candidate(7, lexical_rank=2, lexical_score=0.5, literal_match=True, sources={"lexical"})
    semantic = Candidate(7, semantic_rank=1, semantic_score=0.9, sources={"semantic"})
    merged = deduplicate([lexical, semantic])[7]
    assert merged.sources == {"lexical", "semantic"}
    assert merged.literal_match
    assert merged.lexical_rank == 2
    assert merged.semantic_rank == 1


def test_rrf_prefers_result_present_in_both_branches():
    both = Candidate(1, lexical_rank=5, semantic_rank=5)
    one = Candidate(2, lexical_rank=1)
    assert rrf_score(both) > rrf_score(one)


def test_question_context_is_assigned_only_to_the_following_answer():
    question = "What would you say your greatest fear is?"
    answer = {
        "speaker": "spk:1",
        "start_ms": 39_100,
        "text": "My skill set not being utilized well.",
        "context_before": question,
        "context_before_speaker": "spk:0",
        "context_before_end_ms": 38_100,
    }
    assert _looks_like_question(question)
    pair = _answer_pair_passage(answer)
    assert pair is not None
    assert "QUESTION (spk:0)" in pair
    assert "ANSWER (spk:1)" in pair

    host_question = {
        "speaker": "spk:0",
        "start_ms": 31_300,
        "text": question,
        "context_before": "Let's hop into it with Jordan Noone.",
        "context_before_speaker": "spk:0",
        "context_before_end_ms": 30_300,
    }
    assert _answer_pair_passage(host_question) is None


def test_only_explicit_or_single_term_literals_have_absolute_priority():
    assert _is_strict_literal_query('"money is an instrument of freedom"')
    assert _is_strict_literal_query("Basecamp")
    assert not _is_strict_literal_query("what was Jordan's greatest fear?")
