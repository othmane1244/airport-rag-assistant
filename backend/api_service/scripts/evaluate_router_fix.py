"""Router before/after comparison (fix/router).

- "before" = app/routers/intent.py as on branch main (loaded with `git show`);
- "after"  = the working-tree app/routers/intent.py.
- For every question, the best (smallest) distance among the 8 candidates the
  RAG service returns for /chat, to apply the distance gate.

Modes:
  --tune      (benchmark v2 ONLY) choose the threshold: the smallest value on a
              0.01 grid that blocks no answerable question. Nothing else is tuned.
  --threshold X  apply a fixed threshold (used for the held-out set).

Outputs (rag_service/evaluation/results/router-fix/):
- router accuracy before/after with 95 % Wilson intervals and exact McNemar;
- the "decision" after = router after + distance gate;
- on benchmark v2: config A + router, before/after (Wilson + McNemar),
  using the latest pipeline-A-*.json hits.

Usage (RAG reachable on RAG_SERVICE_URL, e.g. docker-compose.exp.yml):
    python scripts/evaluate_router_fix.py --tune
    python scripts/evaluate_router_fix.py --dataset ../../rag_service/evaluation/router_holdout_v1.json --threshold X
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SERVICE_DIR = Path(__file__).resolve().parents[1]
REPO = SERVICE_DIR.parents[1]
sys.path.insert(0, str(SERVICE_DIR))
os.environ.setdefault("RAG_SERVICE_URL", "http://127.0.0.1:8002")

from app.routers import intent as after_router  # noqa: E402
from app.routers.chat import CANDIDATE_PASSAGES, best_distance  # noqa: E402
from app.services.rag_client import query_knowledge  # noqa: E402

BENCHMARK = REPO / "rag_service" / "evaluation" / "benchmark_v2_150.json"
OUT_DIR = REPO / "rag_service" / "evaluation" / "results" / "router-fix"
PIPELINE_DIR = REPO / "rag_service" / "evaluation" / "results" / "pipeline"


def load_before_router():
    source = subprocess.run(
        ["git", "show", "main:backend/api_service/app/routers/intent.py"],
        cwd=REPO, capture_output=True, check=True,
    ).stdout
    tmp = Path(tempfile.mkdtemp()) / "intent_before.py"
    tmp.write_bytes(source)
    spec = importlib.util.spec_from_file_location("intent_before", tmp)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_intent(case: dict) -> str:
    if case.get("expected_intent"):
        return case["expected_intent"]
    return "flight_status" if case.get("category") == "flight_live" else "documentary"


def wilson(k: int, n: int, z: float = 1.959964):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - h), 4), round(min(1.0, c + h), 4))


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def rate(flags: list[bool]) -> dict:
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return {"correct": k, "n": n, "rate": round(k / n, 4) if n else None, "wilson95": [lo, hi]}


def paired(before: list[bool], after: list[bool]) -> dict:
    b = sum(x and not y for x, y in zip(before, after))
    c = sum(y and not x for x, y in zip(before, after))
    return {"only_before": b, "only_after": c, "mcnemar_exact_p": round(mcnemar_exact(b, c), 4)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", type=Path, default=BENCHMARK)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tune", action="store_true")
    group.add_argument("--threshold", type=float)
    args = parser.parse_args()

    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    dataset_id = data.get("benchmark_id") or data.get("dataset_id")
    if args.tune and dataset_id != "aga-rag-v2-150":
        raise SystemExit("--tune is only allowed on benchmark v2 (aga-rag-v2-150).")

    before_router = load_before_router()
    rows = []
    for case in data["cases"]:
        candidates = query_knowledge(case["query"], n_results=CANDIDATE_PASSAGES)
        rows.append({
            "id": case["id"], "lang": case["lang"], "answerable": case.get("answerable"),
            "kind": case.get("kind") or case.get("category"),
            "expected": expected_intent(case),
            "before": before_router.classify(case["query"]).value,
            "after": after_router.classify(case["query"]).value,
            "best_distance": best_distance(candidates),
        })

    if args.tune:
        answerable = [r["best_distance"] for r in rows if r["answerable"]]
        threshold = math.ceil(max(answerable) * 100) / 100
        rule = "smallest 0.01 grid value above the largest best-distance of the 120 answerable questions"
    else:
        threshold = args.threshold
        rule = "fixed (set on benchmark v2)"

    for r in rows:
        gated = r["best_distance"] is None or r["best_distance"] > threshold
        r["decision_after"] = "distance_threshold" if (r["after"] == "documentary" and gated) else r["after"]

    def ok_router(r, key):
        return r[key] == r["expected"]

    def ok_decision(r):
        # out_of_scope is correctly handled if refused by the router OR stopped by the gate.
        if r["expected"] == "out_of_scope":
            return r["decision_after"] in ("out_of_scope", "distance_threshold")
        return r["decision_after"] == r["expected"]

    def ok_decision_before(r):
        return r["before"] == r["expected"]

    report = {
        "dataset": dataset_id,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "threshold_rule": rule,
        "router_before": rate([ok_router(r, "before") for r in rows]),
        "router_after": rate([ok_router(r, "after") for r in rows]),
        "router_before_vs_after": paired([ok_router(r, "before") for r in rows], [ok_router(r, "after") for r in rows]),
        "decision_after_with_gate": rate([ok_decision(r) for r in rows]),
        "before_vs_decision_after": paired([ok_decision_before(r) for r in rows], [ok_decision(r) for r in rows]),
        "by_language": {
            lang: {
                "router_before": rate([ok_router(r, "before") for r in rows if r["lang"] == lang]),
                "router_after": rate([ok_router(r, "after") for r in rows if r["lang"] == lang]),
                "decision_after_with_gate": rate([ok_decision(r) for r in rows if r["lang"] == lang]),
            }
            for lang in ("fr", "en", "ar")
        },
        "confusion_before": dict(Counter(f"{r['expected']} -> {r['before']}" for r in rows)),
        "confusion_after": dict(Counter(f"{r['expected']} -> {r['after']}" for r in rows)),
        "confusion_decision_after": dict(Counter(f"{r['expected']} -> {r['decision_after']}" for r in rows)),
        "gate": {
            "blocked_answerable": sum(1 for r in rows if r["answerable"] and r["decision_after"] == "distance_threshold"),
            "blocked_unanswerable": sum(1 for r in rows if r["answerable"] is False and r["decision_after"] == "distance_threshold"),
            "blocked_by_expected": dict(Counter(r["expected"] for r in rows if r["decision_after"] == "distance_threshold")),
        },
        "cases": rows,
    }

    if dataset_id == "aga-rag-v2-150":
        a_file = sorted(PIPELINE_DIR.glob("pipeline-A-*.json"))[-1]
        a_hits = {c["id"]: (c["expected_rank"] is not None and c["expected_rank"] <= 3)
                  for c in json.loads(a_file.read_text(encoding="utf-8"))["cases"] if c["answerable"]}
        by_id = {r["id"]: r for r in rows}
        ids = sorted(a_hits)
        before = [a_hits[i] and by_id[i]["before"] == "documentary" for i in ids]
        after = [a_hits[i] and by_id[i]["decision_after"] == "documentary" for i in ids]
        report["a_plus_router"] = {
            "pipeline_file": a_file.name,
            "before": rate(before),
            "after": rate(after),
            "paired": paired(before, after),
            "by_language": {
                lang: {"before": rate([b for i, b in zip(ids, before) if by_id[i]["lang"] == lang]),
                       "after": rate([a for i, a in zip(ids, after) if by_id[i]["lang"] == lang])}
                for lang in ("fr", "en", "ar")
            },
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"router-fix-{dataset_id}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
