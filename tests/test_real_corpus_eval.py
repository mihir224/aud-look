from pathlib import Path

import pytest

from app.evaluation import evaluate, write_report


@pytest.mark.slow
def test_real_corpus_evaluation_writes_ablation_report():
    query_file = Path("eval/queries.yaml")
    if not ("queries:" in query_file.read_text() and "- id:" in query_file.read_text()):
        pytest.skip("Manual real-transcript labels have not been added yet")
    report = evaluate(query_file)
    json_path, markdown_path = write_report(report, Path("eval/reports"))
    assert json_path.exists()
    assert markdown_path.exists()

