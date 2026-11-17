"""Repeatable retrieval-only benchmark for the airport PDF corpus.

Run while the RAG service is available:
    python scripts/evaluate_retrieval.py

The default dataset contains 30 questions balanced across French, English
and Arabic. Results are saved as JSON under evaluation/results/.
This script evaluates source retrieval; it does not call an LLM or grade
generated answers.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_PATH = SCRIPT_DIR.parent / "evaluation" / "benchmark_v1.json"
sys.path.insert(0, str(SCRIPT_DIR.parent))
RAG_URL = os.getenv("RAG_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/")
TOP_K = 5
HIT_K = 3


def _source_groups(case: dict) -> list[list[str]]:
    """Return required source groups; fragments within a group are aliases."""
    if not case.get("answerable", True):
        return []
    groups = case.get("expected_source_groups")
    if groups is not None:
        return groups
    legacy = case.get("expected_sources", [])
    return [legacy] if legacy else []


def _group_ranks(results: list[dict], groups: list[list[str]]) -> list[int | None]:
    ranks: list[int | None] = []
    for group in groups:
        aliases = [fragment.casefold() for fragment in group]
        rank = None
        for index, result in enumerate(results, start=1):
            source = str((result.get("metadata") or {}).get("source_file", "")).casefold()
            if any(fragment in source for fragment in aliases):
                rank = index
                break
        ranks.append(rank)
    return ranks


def _summarize(rows: list[dict]) -> dict:
    count = len(rows)
    answerable = [row for row in rows if row["answerable"]]
    unanswerable = [row for row in rows if not row["answerable"]]
    ranks = [row["expected_rank"] for row in answerable if row["expected_rank"] is not None]
    required_groups = [rank for row in answerable for rank in row["expected_group_ranks"]]
    complete = [row for row in answerable if row["expected_group_ranks"]]
    top_distances = [row["top_distances"][0] for row in unanswerable if row["top_distances"]]
    return {
        "questions": count,
        "answerable_questions": len(answerable),
        "unanswerable_questions": len(unanswerable),
        f"hit_at_{HIT_K}": sum(rank <= HIT_K for rank in ranks) / len(answerable) if answerable else 0.0,
        f"mrr_at_{TOP_K}": sum(1 / rank for rank in ranks) / len(answerable) if answerable else 0.0,
        "required_source_recall_at_5": sum(rank is not None for rank in required_groups) / len(required_groups) if required_groups else 0.0,
        "all_required_sources_hit_at_5": sum(all(rank is not None for rank in row["expected_group_ranks"]) for row in complete) / len(complete) if complete else 0.0,
        "unanswerable_nonempty_retrieval_rate": sum(row["retrieved_count"] > 0 for row in unanswerable) / len(unanswerable) if unanswerable else 0.0,
        "unanswerable_mean_top1_distance": statistics.mean(top_distances) if top_distances else None,
        "mean_retrieval_latency_ms": statistics.mean(row["latency_ms"] for row in rows) if rows else 0.0,
        "median_retrieval_latency_ms": statistics.median(row["latency_ms"] for row in rows) if rows else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    parser.add_argument(
        "--query-expansion",
        action="store_true",
        help="Apply the local deterministic airport-term expansion before retrieval.",
    )
    parser.add_argument(
        "--minimum-hit-at-3",
        type=float,
        help="Optional pass threshold. Without it, the script reports metrics and exits successfully.",
    )
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    if args.query_expansion:
        from app.routers.query import _expand_domain_query
    else:
        _expand_domain_query = lambda query: query
    rows = []
    for case in dataset["cases"]:
        retrieval_query = _expand_domain_query(case["query"])
        started = time.perf_counter()
        response = requests.post(
            f"{RAG_URL}/query",
            json={"query": retrieval_query, "n_results": TOP_K, "audience": "voyageur"},
            timeout=30,
        )
        response.raise_for_status()
        latency_ms = (time.perf_counter() - started) * 1000
        results = response.json().get("results", [])
        groups = _source_groups(case)
        group_ranks = _group_ranks(results, groups)
        matched_ranks = [rank for rank in group_ranks if rank is not None]
        rank = min(matched_ranks) if matched_ranks else None
        top_sources = [
            (result.get("metadata") or {}).get("source_file", "unknown")
            for result in results[:3]
        ]
        row = {
            **case,
            "answerable": case.get("answerable", True),
            "subtype": case.get("subtype", case["category"]),
            "retrieval_query": retrieval_query,
            "expected_rank": rank,
            "expected_group_ranks": group_ranks,
            "hit_at_3": rank is not None and rank <= HIT_K,
            "latency_ms": round(latency_ms, 2),
            "retrieved_count": len(results),
            "top_sources": top_sources,
            "top_distances": [result.get("distance") for result in results[:3]],
        }
        rows.append(row)
        print(
            f"[{case['lang']}/{case['category']}] {case['id']}: "
            f"rank={rank if rank is not None else 'MISS'}; "
            f"top={top_sources[0] if top_sources else 'no result'}; "
            f"{latency_ms:.0f} ms"
        )

    by_language: dict[str, list[dict]] = defaultdict(list)
    by_category: dict[str, list[dict]] = defaultdict(list)
    by_subtype: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_language[row["lang"]].append(row)
        by_category[row["category"]].append(row)
        by_subtype[row["subtype"]].append(row)

    result = {
        "benchmark_id": dataset["benchmark_id"],
        "dataset_description": dataset["description"],
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "rag_url": RAG_URL,
        "top_k": TOP_K,
        "audience_filter": "voyageur",
        "query_expansion_enabled": args.query_expansion,
        "metrics": _summarize(rows),
        "by_language": {key: _summarize(value) for key, value in sorted(by_language.items())},
        "by_category": {key: _summarize(value) for key, value in sorted(by_category.items())},
        "by_subtype": {key: _summarize(value) for key, value in sorted(by_subtype.items())},
        "cases": rows,
        "limitations": [
            "Measures retrieval of an expected source, not answer factuality or citation correctness.",
            "For unanswerable questions, nonempty retrieval and top-1 distance are diagnostics only; they do not measure whether the assistant abstains.",
            "The benchmark questions, translations and expected source groups require domain-expert review before formal reporting.",
        ],
    }

    variant = "-expanded" if args.query_expansion else ""
    output_path = args.output or (
        SCRIPT_DIR.parent / "evaluation" / "results" /
        f"{dataset['benchmark_id']}{variant}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nRetrieval metrics (not generated-answer metrics)")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    print(f"Saved detailed run: {output_path}")
    if args.minimum_hit_at_3 is not None:
        return 0 if result["metrics"][f"hit_at_{HIT_K}"] >= args.minimum_hit_at_3 else 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"RAG benchmark could not reach {RAG_URL}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
