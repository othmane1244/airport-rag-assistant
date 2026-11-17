"""Send the 40 selected questions to POST /chat and save the answers.

Auth: either pass a Keycloak access token (--token or AGA_TOKEN env var),
or run the API with AUTH_DISABLED=true in development mode
(docker-compose.eval.yml). Never use AUTH_DISABLED outside local dev.

The API allows 30 chat requests per minute per account; the default
delay of 2.5 s keeps the run at about 24 requests per minute.

Usage:
    python eval/run_generation.py [--api http://localhost:8001] [--delay 2.5]
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
QUESTIONS = HERE / "questions_40.json"
RESULTS_DIR = HERE / "results"

FIELDS = [
    "id", "lang", "category", "subtype", "answerable", "question",
    "reply", "sources", "engine", "http_status", "latency_ms", "timestamp_utc",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default=os.getenv("AGA_API_URL", "http://localhost:8001"))
    parser.add_argument("--token", default=os.getenv("AGA_TOKEN"))
    parser.add_argument("--delay", type=float, default=2.5, help="Seconds between requests (rate limit: 30/min).")
    args = parser.parse_args()

    api = args.api.rstrip("/")
    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}
    ready = requests.get(f"{api}/ready", timeout=10)
    print(f"/ready -> {ready.status_code} {ready.text[:200]}")
    ready.raise_for_status()

    cases = json.loads(QUESTIONS.read_text(encoding="utf-8"))["cases"]
    RESULTS_DIR.mkdir(exist_ok=True)
    run_at = datetime.now(timezone.utc)
    out_csv = RESULTS_DIR / f"answers-{run_at:%Y%m%dT%H%M%SZ}.csv"

    rows = []
    for i, case in enumerate(cases, 1):
        if i > 1:
            time.sleep(args.delay)
        started = time.perf_counter()
        try:
            resp = requests.post(
                f"{api}/chat",
                json={"message": case["query"], "lang": case["lang"]},
                headers=headers,
                timeout=120,
            )
            status = resp.status_code
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        except requests.RequestException as exc:
            status, body = 0, {"reply": f"REQUEST ERROR: {exc}"}
        latency_ms = round((time.perf_counter() - started) * 1000, 1)

        row = {
            "id": case["id"],
            "lang": case["lang"],
            "category": case["category"],
            "subtype": case.get("subtype") or "",
            "answerable": case["answerable"],
            "question": case["query"],
            "reply": body.get("reply") or body.get("detail") or "",
            "sources": " | ".join(body.get("sources") or []),
            "engine": body.get("engine") or "",
            "http_status": status,
            "latency_ms": latency_ms,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        rows.append(row)
        print(f"[{i:02d}/{len(cases)}] {case['id']:<32} {status} engine={row['engine'] or '?':<18} {latency_ms:>8.0f} ms")

    # utf-8-sig so Excel shows Arabic text correctly.
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    engines = {}
    for r in rows:
        engines[r["engine"] or "unknown"] = engines.get(r["engine"] or "unknown", 0) + 1
    print(f"\nSaved {out_csv}")
    print("Engines:", json.dumps(engines))
    print("Non-200 responses:", sum(1 for r in rows if r["http_status"] != 200))


if __name__ == "__main__":
    main()
