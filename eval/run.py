from pathlib import Path

from app.evaluation import evaluate, write_report


if __name__ == "__main__":
    report = evaluate(Path("eval/queries.yaml"))
    paths = write_report(report, Path("eval/reports"))
    print(f"Wrote {paths[0]} and {paths[1]}")

