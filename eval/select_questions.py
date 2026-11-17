"""Select the 40-question generation-evaluation sample from benchmark v2.

- 30 answerable questions: 10 per language (fr, en, ar), stratified by
  category in proportion to the benchmark (transport 3, services 3,
  medical 1, accessibility 1, airport_info 1, formalites 1).
- 10 unanswerable questions: 3 fr, 3 en, 4 ar.
- 10 of the 40 are flagged for double annotation (inter-annotator
  agreement): 7 answerable + 3 unanswerable.

The seed is fixed so the selection is reproducible.

Usage: python eval/select_questions.py
"""
import json
import random
from collections import defaultdict
from pathlib import Path

SEED = 20261108
ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "rag_service" / "evaluation" / "benchmark_v2_150.json"
OUT = Path(__file__).resolve().parent / "questions_40.json"

ANSWERABLE_PER_CATEGORY = {
    "transport": 3,
    "services": 3,
    "medical": 1,
    "accessibility": 1,
    "airport_info": 1,
    "formalites": 1,
}
UNANSWERABLE_PER_LANG = {"fr": 3, "en": 3, "ar": 4}
LANGS = ("fr", "en", "ar")


def main() -> None:
    data = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    rng = random.Random(SEED)

    by_key = defaultdict(list)
    for case in data["cases"]:
        by_key[(case["lang"], case["answerable"], case["category"] if case["answerable"] else None)].append(case)

    selected = []
    for lang in LANGS:
        for category, n in ANSWERABLE_PER_CATEGORY.items():
            pool = sorted(by_key[(lang, True, category)], key=lambda c: c["id"])
            selected.extend(rng.sample(pool, n))
    for lang in LANGS:
        pool = sorted(by_key[(lang, False, None)], key=lambda c: c["id"])
        selected.extend(rng.sample(pool, UNANSWERABLE_PER_LANG[lang]))

    answerable_ids = [c["id"] for c in selected if c["answerable"]]
    unanswerable_ids = [c["id"] for c in selected if not c["answerable"]]
    double = set(rng.sample(answerable_ids, 7)) | set(rng.sample(unanswerable_ids, 3))

    cases = [
        {
            "id": c["id"],
            "lang": c["lang"],
            "category": c["category"],
            "subtype": c.get("subtype"),
            "answerable": c["answerable"],
            "query": c["query"],
            "expected_source_groups": c.get("expected_source_groups", []),
            "double_annotation": c["id"] in double,
        }
        for c in selected
    ]
    out = {
        "source_benchmark": data["benchmark_id"],
        "seed": SEED,
        "counts": {
            "total": len(cases),
            "answerable": len(answerable_ids),
            "unanswerable": len(unanswerable_ids),
            "double_annotation": len(double),
        },
        "cases": cases,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(cases)} questions, {len(double)} for double annotation)")


if __name__ == "__main__":
    main()
