"""Review topical source filtering against the 30-query airport FAQ pilot.

This reuses the API's production source filter and calls only the local RAG
service. It makes no LLM or paid-provider requests.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR.parent))
from app.routers.chat import _filter_topic_chunks  # noqa: E402

DATASET_PATH = REPO_DIR / "rag_service" / "evaluation" / "benchmark_v1.json"
OUTPUT_PATH = REPO_DIR / "rag_service" / "evaluation" / "results" / "citation-review-20261010.json"
RAG_URL = os.getenv("RAG_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/")


def _matches_expected(chunk: dict, expected_sources: list[str]) -> bool:
    source = str((chunk.get("metadata") or {}).get("source_file", "")).casefold()
    return any(fragment.casefold() in source for fragment in expected_sources)


def _unique_sources(chunks: list[dict]) -> list[str]:
    return list(
        dict.fromkeys(
            str((chunk.get("metadata") or {}).get("source_file", ""))
            for chunk in chunks
        )
    )


def main() -> int:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    rows = []
    for case in dataset["cases"]:
        response = requests.post(
            f"{RAG_URL}/query",
            json={"query": case["query"], "n_results": 3, "audience": "voyageur"},
            timeout=30,
        )
        response.raise_for_status()
        chunks = response.json().get("results", [])
        filtered = _filter_topic_chunks(case["query"], chunks)
        before_expected = any(_matches_expected(chunk, case["expected_sources"]) for chunk in chunks)
        after_expected = any(_matches_expected(chunk, case["expected_sources"]) for chunk in filtered)
        row = {
            "id": case["id"],
            "lang": case["lang"],
            "expected_source_found_before_filter": before_expected,
            "expected_source_found_after_filter": after_expected,
            "sources_before": _unique_sources(chunks),
            "sources_after": _unique_sources(filtered),
        }
        rows.append(row)
        print(
            f"{case['id']}: {'OK' if after_expected else 'MISSING'}; "
            f"citations {len(chunks)} -> {len(filtered)}"
        )

    result = {
        "benchmark_id": dataset["benchmark_id"],
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "retrieval_limit": 3,
        "expected_source_preserved": sum(row["expected_source_found_after_filter"] for row in rows),
        "questions": len(rows),
        "citation_count_before": sum(len(row["sources_before"]) for row in rows),
        "citation_count_after": sum(len(row["sources_after"]) for row in rows),
        "cases": rows,
        "limitations": [
            "Checks expected-source preservation and citation filtering, not generated-answer factuality.",
            "The benchmark is a manually authored 30-question pilot and needs domain review.",
        ],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"\nExpected source preserved: {result['expected_source_preserved']}/{result['questions']}"
        f"\nCitation labels: {result['citation_count_before']} -> {result['citation_count_after']}"
        f"\nSaved: {OUTPUT_PATH}"
    )
    return 0 if result["expected_source_preserved"] == result["questions"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
