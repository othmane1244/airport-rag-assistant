"""Send the 14 'confusable' off-topic questions of router_holdout_v1 to POST /chat
and save engine, reply and sources for manual classification.

Usage (local stack, auth bypass via docker-compose.eval.yml, or --token):
    python eval/run_confusable_chat.py [--api http://localhost:8001] [--delay 4]
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT = ROOT / "rag_service" / "evaluation" / "router_holdout_v1.json"
OUT_DIR = ROOT / "rag_service" / "evaluation" / "results" / "router-fix"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=os.getenv("AGA_API_URL", "http://localhost:8001"))
    parser.add_argument("--token", default=os.getenv("AGA_TOKEN"))
    parser.add_argument("--delay", type=float, default=4.0)
    args = parser.parse_args()
    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}

    cases = [c for c in json.loads(HOLDOUT.read_text(encoding="utf-8"))["cases"] if c["kind"] == "confusable"]
    rows = []
    for i, case in enumerate(cases, 1):
        if i > 1:
            time.sleep(args.delay)
        t0 = time.perf_counter()
        r = requests.post(f"{args.api.rstrip('/')}/chat", json={"message": case["query"], "lang": case["lang"]},
                          headers=headers, timeout=120)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        rows.append({
            "id": case["id"], "lang": case["lang"], "question": case["query"],
            "http_status": r.status_code, "engine": body.get("engine"),
            "sources": body.get("sources") or [], "reply": body.get("reply") or body.get("detail"),
            "latency_ms": round((time.perf_counter() - t0) * 1000),
        })
        print(f"[{i:02d}/{len(cases)}] {case['id']} HTTP {r.status_code} engine={body.get('engine')}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"confusable-chat-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps({"holdout": "aga-router-holdout-v1", "kind": "confusable",
                               "run_at_utc": datetime.now(timezone.utc).isoformat(), "rows": rows},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
