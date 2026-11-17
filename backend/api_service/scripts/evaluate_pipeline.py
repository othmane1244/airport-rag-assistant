"""Evaluate the real /chat retrieval chain on the 150-question benchmark.

Chain (imported from app.routers.chat, not copied):
    8 candidates from the RAG service
    -> topic filter (_TOPIC_SOURCE_RULES), if enabled
    -> cross-encoder reranker (POST /rerank), if enabled
    -> the first 3 passages are what the LLM receives.

Metrics (same source-matching helpers as rag_service/scripts/evaluate_retrieval.py):
- Hit@3: an expected source group is among the 3 passages sent to the LLM;
- MRR@5 and required-source recall@5: on the first 5 passages of the
  ordered list, before the cut to 3 (after filtering the list can be shorter);
- zero-passage questions: the chain returned nothing, /chat answers "no document found";
- latency of the whole retrieval chain (RAG call + rerank), client side.

Query expansion lives in the RAG service (RAG_QUERY_EXPANSION); the script reads
its state from GET /health and refuses to run if it does not match the config.

Usage (RAG service reachable, e.g. docker-compose.exp.yml publishes 127.0.0.1:8002):
    set RAG_SERVICE_URL=http://127.0.0.1:8002
    python scripts/evaluate_pipeline.py --config A
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_DIR.parents[1]
sys.path.insert(0, str(SERVICE_DIR))
os.environ.setdefault("RAG_SERVICE_URL", "http://127.0.0.1:8002")

import requests  # noqa: E402

from app.config import settings  # noqa: E402
from app.routers.chat import CONTEXT_PASSAGES, rank_candidate_chunks  # noqa: E402


def _load_retrieval_helpers():
    path = REPO_ROOT / "rag_service" / "scripts" / "evaluate_retrieval.py"
    saved_path = list(sys.path)
    spec = importlib.util.spec_from_file_location("evaluate_retrieval", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path[:] = saved_path  # the helper prepends rag_service/ to sys.path
    return module._source_groups, module._group_ranks


_source_groups, _group_ranks = _load_retrieval_helpers()

CONFIGS = {
    "A": {"expansion": True, "topic_filter": True, "reranker": False, "label": "current: expansion + topic filter"},
    "B": {"expansion": True, "topic_filter": False, "reranker": False, "label": "expansion only"},
    "C": {"expansion": True, "topic_filter": False, "reranker": True, "label": "expansion + reranker"},
    "D": {"expansion": False, "topic_filter": False, "reranker": False, "label": "raw dense retrieval"},
}
MRR_K = 5
DATASET = REPO_ROOT / "rag_service" / "evaluation" / "benchmark_v2_150.json"
OUT_DIR = REPO_ROOT / "rag_service" / "evaluation" / "results" / "pipeline"


def summarize(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["answerable"]]
    unans = [r for r in rows if not r["answerable"]]
    ranks = [r["expected_rank"] for r in ans]
    groups = [g for r in ans for g in r["expected_group_ranks"]]
    lat = [r["latency_ms"] for r in rows]
    n = len(ans)
    return {
        "questions": len(rows),
        "answerable_questions": n,
        "hit_at_3": sum(r is not None and r <= CONTEXT_PASSAGES for r in ranks) / n if n else None,
        "mrr_at_5": sum(1 / r for r in ranks if r is not None) / n if n else None,
        "required_source_recall_at_5": sum(g is not None for g in groups) / len(groups) if groups else None,
        "all_required_sources_hit_at_5": sum(all(g is not None for g in r["expected_group_ranks"]) for r in ans) / n if n else None,
        "zero_passage_answerable": sum(r["final_count"] == 0 for r in ans),
        "zero_passage_unanswerable": sum(r["final_count"] == 0 for r in unans),
        "mean_latency_ms": round(statistics.mean(lat), 1) if lat else None,
        "median_latency_ms": round(statistics.median(lat), 1) if lat else None,
        "p95_latency_ms": round(sorted(lat)[max(0, int(0.95 * len(lat)) - 1)], 1) if lat else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", choices=sorted(CONFIGS), required=True)
    parser.add_argument("--dataset", type=Path, default=DATASET)
    args = parser.parse_args()
    cfg = CONFIGS[args.config]

    health = requests.get(f"{settings.rag_service_url.rstrip('/')}/health", timeout=10).json()
    if health.get("query_expansion") is not cfg["expansion"]:
        print(f"RAG service has query_expansion={health.get('query_expansion')}, config {args.config} needs "
              f"{cfg['expansion']}. Restart rag with RAG_QUERY_EXPANSION={str(cfg['expansion']).lower()}.")
        return 2
    if cfg["reranker"]:  # load the model before timing
        rank_candidate_chunks("warm-up", topic_filter=False, reranker=True)

    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    rows = []
    for i, case in enumerate(data["cases"], 1):
        started = time.perf_counter()
        ranked = rank_candidate_chunks(case["query"], topic_filter=cfg["topic_filter"], reranker=cfg["reranker"])
        latency = (time.perf_counter() - started) * 1000
        groups = _source_groups(case)
        group_ranks = _group_ranks(ranked[:MRR_K], groups)
        found = [r for r in group_ranks if r is not None]
        rows.append({
            "id": case["id"], "lang": case["lang"], "category": case["category"],
            "answerable": case["answerable"],
            "candidates_after_chain": len(ranked),
            "final_count": len(ranked[:CONTEXT_PASSAGES]),
            "expected_rank": min(found) if found else None,
            "expected_group_ranks": group_ranks,
            "final_sources": [(c.get("metadata") or {}).get("source_file", "?") for c in ranked[:CONTEXT_PASSAGES]],
            "latency_ms": round(latency, 1),
        })
        if i % 25 == 0:
            print(f"  {i}/{len(data['cases'])}")

    result = {
        "benchmark_id": data["benchmark_id"],
        "config": args.config,
        "config_detail": {k: v for k, v in cfg.items()},
        "candidates": 8,
        "context_passages": CONTEXT_PASSAGES,
        "reranker_model": health.get("reranker_model") or "BAAI/bge-reranker-v2-m3" if cfg["reranker"] else None,
        "rag_health": health,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "metrics": summarize(rows),
        "by_language": {lang: summarize([r for r in rows if r["lang"] == lang]) for lang in ("fr", "en", "ar")},
        "cases": rows,
        "notes": [
            "Hit@3 is measured on the passages actually sent to the LLM; MRR@5 and recall@5 on the ordered list before the cut to 3.",
            "The topic rules and the query expansion were tuned while looking at this same question set.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"pipeline-{args.config}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"config": args.config, **result["metrics"]}, indent=2))
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
