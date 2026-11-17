"""Compute generation-quality percentages from a filled annotation grid,
and inter-annotator agreement when a second grid is given.

Usage:
    python eval/score.py GRID_A.xlsx [GRID_B.xlsx]

Output: a summary printed to the console and saved as JSON next to GRID_A
(<grid>-scores.json). Empty rating cells are counted as "not rated" and
excluded from percentages; the summary reports how many are missing.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook

CRITERIA_ANSWERABLE = ("exactitude", "fidele_source", "bonne_langue")
CRITERIA_UNANSWERABLE = ("abstention_correcte", "bonne_langue")
ALLOWED = {
    "exactitude": {"exacte", "partielle", "fausse"},
    "fidele_source": {"oui", "non"},
    "bonne_langue": {"oui", "non"},
    "abstention_correcte": {"oui", "non"},
}


def load(path: Path) -> list[dict]:
    ws = load_workbook(path, read_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h) for h in rows[0]]
    out = []
    for values in rows[1:]:
        row = dict(zip(header, values))
        if not row.get("id"):
            continue
        row["answerable"] = str(row["answerable"]).strip().lower() in {"true", "1", "vrai"}
        for c in ALLOWED:
            v = row.get(c)
            v = str(v).strip().lower() if v is not None else ""
            if v and v not in ALLOWED[c]:
                raise SystemExit(f"{path.name}: invalid value {v!r} for {c} in row {row['id']}")
            row[c] = v
        out.append(row)
    return out


def distribution(rows: list[dict], criterion: str) -> dict:
    values = [r[criterion] for r in rows if r[criterion]]
    counts = Counter(values)
    n = len(values)
    return {
        "rated": n,
        "not_rated": len(rows) - n,
        "percent": {k: round(100 * counts[k] / n, 1) for k in sorted(ALLOWED[criterion])} if n else {},
    }


def summarize(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["answerable"]]
    unans = [r for r in rows if not r["answerable"]]
    result = {
        "answerable": {"n": len(ans), **{c: distribution(ans, c) for c in CRITERIA_ANSWERABLE}},
        "unanswerable": {"n": len(unans), **{c: distribution(unans, c) for c in CRITERIA_UNANSWERABLE}},
    }
    for key in ("lang", "engine"):
        groups = defaultdict(list)
        for r in rows:
            groups[r.get(key) or "unknown"].append(r)
        result[f"by_{key}"] = {
            g: {
                "answerable_exactitude": distribution([r for r in rs if r["answerable"]], "exactitude"),
                "answerable_fidele_source": distribution([r for r in rs if r["answerable"]], "fidele_source"),
                "unanswerable_abstention": distribution([r for r in rs if not r["answerable"]], "abstention_correcte"),
                "bonne_langue": distribution(rs, "bonne_langue"),
            }
            for g, rs in sorted(groups.items())
        }
    return result


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if pe == 1:
        return None  # both annotators used a single identical label: kappa undefined
    return round((po - pe) / (1 - pe), 3)


def agreement(rows_a: list[dict], rows_b: list[dict]) -> dict:
    a_by_id = {r["id"]: r for r in rows_a}
    out = {}
    for c in ALLOWED:
        pairs = []
        for rb in rows_b:
            ra = a_by_id.get(rb["id"])
            if ra is None:
                continue
            applies = c in (CRITERIA_ANSWERABLE if rb["answerable"] else CRITERIA_UNANSWERABLE)
            if applies and ra[c] and rb[c]:
                pairs.append((ra[c], rb[c]))
        if not pairs:
            out[c] = {"pairs": 0}
            continue
        xs, ys = zip(*pairs)
        out[c] = {
            "pairs": len(pairs),
            "raw_agreement_percent": round(100 * sum(x == y for x, y in pairs) / len(pairs), 1),
            "cohen_kappa": cohen_kappa(list(xs), list(ys)),
        }
    return out


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    grid_a = Path(sys.argv[1])
    rows_a = load(grid_a)
    report = {"grid": grid_a.name, "scores": summarize(rows_a)}
    if len(sys.argv) == 3:
        grid_b = Path(sys.argv[2])
        report["agreement"] = {"grid_b": grid_b.name, "criteria": agreement(rows_a, load(grid_b))}

    out = grid_a.with_name(grid_a.stem + "-scores.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
