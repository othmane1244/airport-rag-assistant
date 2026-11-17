"""Measure the keyword intent router (app.routers.intent.classify) on the
150-question benchmark. No service and no LLM call is needed.

Expected intent (labelling rule, chosen for this benchmark):
- category "flight_live" (live flight status, gate, delays) -> flight_status:
  the designed behaviour is the redirect to the official ONDA flight search;
- every other question -> documentary: all benchmark questions are about the
  airport, including the unanswerable ones, which should reach the RAG and
  then be answered with an abstention.
The benchmark contains no truly out-of-scope question, so the router's
ability to reject off-topic messages is NOT measured here; only wrong
"out_of_scope" decisions on in-scope questions are.

A dataset may instead carry an explicit "expected_intent" per case (e.g.
rag_service/evaluation/router_holdout_v1.json, a held-out set never used for
tuning); that label is then used and the rule above is ignored.

Usage:
    python scripts/evaluate_router.py                                  # benchmark v2
    python scripts/evaluate_router.py --dataset ../../rag_service/evaluation/router_holdout_v1.json
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_DIR.parents[1]
sys.path.insert(0, str(SERVICE_DIR))

from app.routers.intent import Intent, classify  # noqa: E402

DATASET = REPO_ROOT / "rag_service" / "evaluation" / "benchmark_v2_150.json"
OUT_DIR = REPO_ROOT / "rag_service" / "evaluation" / "results" / "pipeline"
LABELS = [i.value for i in Intent]


def expected_intent(case: dict) -> str:
    if case.get("expected_intent"):
        return case["expected_intent"]
    return Intent.FLIGHT_STATUS.value if case["category"] == "flight_live" else Intent.DOCUMENTARY.value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    args = parser.parse_args()
    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    dataset_id = data.get("benchmark_id") or data.get("dataset_id")
    explicit = all("expected_intent" in c for c in data["cases"])
    rows = [
        {"id": c["id"], "lang": c["lang"], "category": c["category"], "answerable": c["answerable"],
         "expected": expected_intent(c), "predicted": classify(c["query"]).value}
        for c in data["cases"]
    ]
    confusion = {e: {p: 0 for p in LABELS} for e in LABELS}
    for r in rows:
        confusion[r["expected"]][r["predicted"]] += 1

    def acc(rs):
        return round(sum(r["expected"] == r["predicted"] for r in rs) / len(rs), 4) if rs else None

    per_class = {}
    for label in LABELS:
        tp = confusion[label][label]
        pred = sum(confusion[e][label] for e in LABELS)
        true = sum(confusion[label].values())
        per_class[label] = {
            "support": true,
            "precision": round(tp / pred, 4) if pred else None,
            "recall": round(tp / true, 4) if true else None,
        }
    result = {
        "benchmark_id": dataset_id,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "labelling_rule": "explicit expected_intent per case" if explicit else "flight_live -> flight_status; all other questions -> documentary",
        "accuracy": acc(rows),
        "accuracy_by_language": {l: acc([r for r in rows if r["lang"] == l]) for l in ("fr", "en", "ar")},
        "per_class": per_class,
        "confusion_matrix_expected_rows_predicted_columns": confusion,
        "errors": [r for r in rows if r["expected"] != r["predicted"]],
        "limitations": [] if explicit else [
            "No out-of-scope question in the benchmark: rejection of off-topic messages is not measured.",
            "The keyword lists were written while looking at airport questions similar to these.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = "" if dataset_id == "aga-rag-v2-150" else f"{dataset_id}-"
    out = OUT_DIR / f"router-{tag}{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("accuracy", "accuracy_by_language", "per_class",
                                             "confusion_matrix_expected_rows_predicted_columns")}, indent=2))
    print("errors:", Counter((e["expected"], e["predicted"]) for e in result["errors"]))
    for e in result["errors"]:
        print("  ", e["id"], e["expected"], "->", e["predicted"])
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
