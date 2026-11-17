"""Build the comparison table from the latest pipeline-*.json, router-*.json
and chunking-*.json files in rag_service/evaluation/results/pipeline/.

Adds a row "A + router": config A where answerable questions that the keyword
router sends to out_of_scope / flight_status count as misses with 0 passages,
which is what /chat actually does.

Statistics on Hit@3 (120 answerable questions):
- 95 % Wilson score interval for each configuration;
- exact McNemar test (two-sided binomial test on the discordant pairs)
  for A vs B (topic filter) and B vs D (query expansion).

Usage: python scripts/compare_pipeline.py
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESULTS = Path(__file__).resolve().parents[3] / "rag_service" / "evaluation" / "results" / "pipeline"


def latest(pattern: str):
    files = sorted(RESULTS.glob(pattern))
    return (json.loads(files[-1].read_text(encoding="utf-8")), files[-1].name) if files else (None, None)


def pct(x):
    return "–" if x is None else f"{100 * x:.1f} %"


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """95 % Wilson score interval for a proportion k/n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value: binomial(b + c, 0.5) on discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def hits(data: dict) -> dict:
    return {r["id"]: (r["expected_rank"] is not None and r["expected_rank"] <= 3)
            for r in data["cases"] if r["answerable"]}


def ci_text(data: dict) -> str:
    h = hits(data)
    lo, hi = wilson(sum(h.values()), len(h))
    return f"[{100 * lo:.1f} ; {100 * hi:.1f}]"


def with_router(a: dict, router: dict) -> dict:
    predicted = {e["id"]: e["predicted"] for e in router["errors"]}
    rows = a["cases"]

    def summ(rs):
        ans = [r for r in rs if r["answerable"]]
        blocked = [r for r in ans if predicted.get(r["id"], "documentary") != "documentary"]
        ok = [r for r in ans if r not in blocked]
        groups = [g for r in ok for g in r["expected_group_ranks"]] + [None] * sum(len(r["expected_group_ranks"]) for r in blocked)
        return {
            "hit_at_3": sum(r["expected_rank"] is not None and r["expected_rank"] <= 3 for r in ok) / len(ans),
            "mrr_at_5": sum(1 / r["expected_rank"] for r in ok if r["expected_rank"]) / len(ans),
            "required_source_recall_at_5": sum(g is not None for g in groups) / len(groups),
            "zero_passage_answerable": sum(r["final_count"] == 0 for r in ok) + len(blocked),
            "blocked_by_router": len(blocked),
        }

    return {"metrics": summ(rows), "by_language": {l: summ([r for r in rows if r["lang"] == l]) for l in ("fr", "en", "ar")}}


def main() -> None:
    runs = {c: latest(f"pipeline-{c}-*.json") for c in "ABCD"}
    router, router_file = latest("router-*.json")
    chunking, chunking_file = latest("chunking-*.json")

    lines = ["# Retrieval pipeline comparison", "",
             f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from:", ""]
    for c, (data, name) in runs.items():
        lines.append(f"- {c}: `{name}`" if data else f"- {c}: **not run**")
    lines += [f"- router: `{router_file}`", f"- chunking: `{chunking_file}`", "",
              "## Overall (120 answerable questions; latency on 150)", "",
              "| Config | Expansion | Topic filter | Reranker | Hit@3 | Hit@3 95 % CI (Wilson) | MRR@5 | Recall@5 | 0 passage (answerable) | Median latency |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for c, (data, _) in runs.items():
        if not data:
            lines.append(f"| {c} | | | | not run | | | | | |")
            continue
        d, m = data["config_detail"], data["metrics"]
        yn = lambda v: "yes" if v else "no"  # noqa: E731
        lines.append(f"| {c} | {yn(d['expansion'])} | {yn(d['topic_filter'])} | {yn(d['reranker'])} | {pct(m['hit_at_3'])} | {ci_text(data)} | "
                     f"{m['mrr_at_5']:.3f} | {pct(m['required_source_recall_at_5'])} | {m['zero_passage_answerable']} | {m['median_latency_ms']:.0f} ms |")
    a = runs["A"][0]
    if a and router:
        wr = with_router(a, router)
        m = wr["metrics"]
        k = round(m["hit_at_3"] * 120)
        lo, hi = wilson(k, 120)
        lines.append(f"| A + router | yes | yes | no | {pct(m['hit_at_3'])} | [{100 * lo:.1f} ; {100 * hi:.1f}] | {m['mrr_at_5']:.3f} | {pct(m['required_source_recall_at_5'])} | "
                     f"{m['zero_passage_answerable']} (of which {m['blocked_by_router']} blocked by the router) | – |")

    lines += ["", "## Significance of Hit@3 differences (exact McNemar, two-sided)", "",
              "| Comparison | What changes | Only first hits | Only second hits | p-value | Reading |", "|---|---|---|---|---|---|"]
    for x, y, what in (("A", "B", "topic filter"), ("B", "D", "query expansion")):
        if runs[x][0] and runs[y][0]:
            hx, hy = hits(runs[x][0]), hits(runs[y][0])
            b = sum(hx[k] and not hy[k] for k in hx)
            c = sum(hy[k] and not hx[k] for k in hx)
            p = mcnemar_exact(b, c)
            reading = "significant at 5 %" if p < 0.05 else "not significant: a trend only"
            lines.append(f"| {x} vs {y} | {what} | {b} | {c} | {p:.3f} | {reading} |")

    lines += ["", "## Hit@3 by language", "", "| Config | fr | en | ar |", "|---|---|---|---|"]
    for c, (data, _) in runs.items():
        if data:
            bl = data["by_language"]
            lines.append(f"| {c} | {pct(bl['fr']['hit_at_3'])} | {pct(bl['en']['hit_at_3'])} | {pct(bl['ar']['hit_at_3'])} |")
    if a and router:
        bl = with_router(a, router)["by_language"]
        lines.append(f"| A + router | {pct(bl['fr']['hit_at_3'])} | {pct(bl['en']['hit_at_3'])} | {pct(bl['ar']['hit_at_3'])} |")

    if router:
        cm = router["confusion_matrix_expected_rows_predicted_columns"]
        labels = ["documentary", "flight_status", "out_of_scope", "greeting"]
        lines += ["", "## Keyword router (150 questions)", "",
                  f"Accuracy {pct(router['accuracy'])} (fr {pct(router['accuracy_by_language']['fr'])}, "
                  f"en {pct(router['accuracy_by_language']['en'])}, ar {pct(router['accuracy_by_language']['ar'])}). "
                  f"Labelling rule: {router['labelling_rule']}.", "",
                  "| expected \\ predicted | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
        for e in ("documentary", "flight_status"):
            lines.append(f"| {e} | " + " | ".join(str(cm[e][p]) for p in labels) + " |")

    if chunking:
        lines += ["", "## Chunk size (voyageur PDFs rebuilt in separate collections; expansion on, no filter, no reranker)", "",
                  "| Chunk / overlap | Passages | Mean chars | Hit@3 | MRR@5 | Recall@5 | Hit@3 fr / en / ar |", "|---|---|---|---|---|---|---|"]
        for size, s in chunking["sizes"].items():
            m, bl = s["metrics"], s["by_language"]
            lines.append(f"| {size}/{chunking['overlap']} | {s['passages']} | {s['mean_passage_chars']} | {pct(m['hit_at_3'])} | {m['mrr_at_5']:.3f} | "
                         f"{pct(m['required_source_recall_at_5'])} | {pct(bl['fr']['hit_at_3'])} / {pct(bl['en']['hit_at_3'])} / {pct(bl['ar']['hit_at_3'])} |")
        lines.append(f"\nMain index holds {chunking['main_index_passages_for_these_pdfs']} passages for these PDFs; the 1200/150 rebuild is not identical to it.")

    out = RESULTS / f"summary-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
