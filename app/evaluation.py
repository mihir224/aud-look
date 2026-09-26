import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from time import perf_counter

import yaml

from app.retrieval.hybrid import EVALUATION_STRATEGIES, search


def overlaps(result: dict, span: dict) -> bool:
    if result["audio_slug"] != span["audio_slug"]:
        return False
    intersection = max(0, min(result["end_ms"], span["end_ms"]) - max(result["start_ms"], span["start_ms"]))
    shorter = min(result["end_ms"] - result["start_ms"], span["end_ms"] - span["start_ms"])
    return shorter > 0 and intersection / shorter >= 0.5


def evaluate(query_path: Path, split: str = "holdout", strategies: list[str] | None = None) -> dict:
    data = yaml.safe_load(query_path.read_text()) or {}
    queries = [query for query in data.get("queries", []) if query.get("split") == split]
    if not queries:
        raise ValueError(f"No {split} queries found in {query_path}; label the real transcripts first.")
    strategies = strategies or ["lexical", "semantic", "rrf", "hybrid", "hybrid_alt"]
    unknown = set(strategies) - EVALUATION_STRATEGIES
    if unknown:
        raise ValueError(f"Unknown evaluation strategies: {sorted(unknown)}")
    report = {"split": split, "query_count": len(queries), "strategies": {}}
    for strategy in strategies:
        # The submission reports warm latency. Load models, establish database
        # connections, and exercise the strategy once outside the timed sample.
        search(queries[0]["query"], k=5, strategy=strategy)
        recall = {1: [], 3: [], 5: []}
        hit_rate = {1: [], 3: [], 5: []}
        reciprocal_ranks = []
        latencies = []
        per_category: dict[str, list[float]] = defaultdict(list)
        for query in queries:
            started = perf_counter()
            results = search(query["query"], k=5, strategy=strategy).results
            latencies.append((perf_counter() - started) * 1000)
            ranks = []
            for rank, result in enumerate(results, start=1):
                if any(overlaps(result.model_dump(), span) for span in query["relevant_spans"]):
                    ranks.append(rank)
            for k in recall:
                matched_spans = sum(any(overlaps(result.model_dump(), span) for result in results[:k]) for span in query["relevant_spans"])
                recall[k].append(matched_spans / len(query["relevant_spans"]))
                hit_rate[k].append(1.0 if any(rank <= k for rank in ranks) else 0.0)
            reciprocal_ranks.append(1 / min(ranks) if ranks else 0.0)
            per_category[query["category"]].append(1.0 if any(rank <= 5 for rank in ranks) else 0.0)
        sorted_latencies = sorted(latencies)
        report["strategies"][strategy] = {
            "recall_at": {str(k): sum(values) / len(values) for k, values in recall.items()},
            "hit_rate_at": {str(k): sum(values) / len(values) for k, values in hit_rate.items()},
            "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
            "latency_ms": {"p50": median(latencies), "p95": sorted_latencies[max(0, int(len(sorted_latencies) * 0.95) - 1)]},
            "recall_at_5_by_category": {category: sum(values) / len(values) for category, values in per_category.items()},
        }
    return report


def write_report(report: dict, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "evaluation.json"
    markdown_path = output_dir / "evaluation.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Retrieval Evaluation", "", f"Split: `{report['split']}`; queries: {report['query_count']}", "", "| Strategy | R@1 | R@3 | R@5 | MRR | p95 ms |", "|---|---:|---:|---:|---:|---:|"]
    for strategy, metrics in report["strategies"].items():
        lines.append(
            f"| {strategy} | {metrics['recall_at']['1']:.3f} | {metrics['recall_at']['3']:.3f} | {metrics['recall_at']['5']:.3f} | {metrics['mrr']:.3f} | {metrics['latency_ms']['p95']:.0f} |"
        )
    markdown_path.write_text("\n".join(lines) + "\n")
    return json_path, markdown_path
