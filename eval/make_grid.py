"""Build the empty annotation grids from an answers CSV.

Creates two Excel files next to the answers file:
- <answers>-grid-A.xlsx : all 40 answers, for the main annotator;
- <answers>-grid-B.xlsx : the 10 answers flagged for double annotation,
  for the second annotator (inter-annotator agreement).

The rating columns are left EMPTY. Each has a drop-down list of allowed
values. Cells that do not apply to a row are greyed out:
- answerable questions: exactitude, fidele_source, bonne_langue;
- unanswerable questions: abstention_correcte, bonne_langue.

Usage: python eval/make_grid.py eval/results/answers-<timestamp>.csv
"""
import csv
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
QUESTIONS = HERE / "questions_40.json"

INFO_COLS = ["id", "lang", "category", "answerable", "question", "expected_sources", "reply", "sources", "engine"]
RATING_COLS = {
    "exactitude": ["exacte", "partielle", "fausse"],
    "fidele_source": ["oui", "non"],
    "bonne_langue": ["oui", "non"],
    "abstention_correcte": ["oui", "non"],
    "commentaire": None,
}
APPLIES = {
    True: {"exactitude", "fidele_source", "bonne_langue", "commentaire"},
    False: {"abstention_correcte", "bonne_langue", "commentaire"},
}
WIDTHS = {"id": 26, "lang": 6, "category": 13, "answerable": 11, "question": 40, "expected_sources": 24,
          "reply": 70, "sources": 34, "engine": 16, "commentaire": 40}
GREY = PatternFill("solid", fgColor="D9D9D9")
HEADER = PatternFill("solid", fgColor="1F3864")


def build(rows: list[dict], path: Path, title: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = title
    columns = INFO_COLS + list(RATING_COLS)
    ws.append(columns)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER
    for row in rows:
        ws.append([row[c] for c in INFO_COLS] + [None] * len(RATING_COLS))

    n = len(rows) + 1
    for name, values in RATING_COLS.items():
        if not values:
            continue
        col = ws.cell(row=1, column=columns.index(name) + 1).column_letter
        dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{col}2:{col}{n}")

    for r, row in enumerate(rows, start=2):
        applies = APPLIES[row["answerable"]]
        for name in RATING_COLS:
            if name not in applies:
                ws.cell(row=r, column=columns.index(name) + 1).fill = GREY
        for c in range(1, len(columns) + 1):
            ws.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical="top")

    for i, name in enumerate(columns, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = WIDTHS.get(name, 14)
    ws.freeze_panes = "B2"
    wb.save(path)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    answers_path = Path(sys.argv[1])
    questions = {c["id"]: c for c in json.loads(QUESTIONS.read_text(encoding="utf-8"))["cases"]}
    with answers_path.open(encoding="utf-8-sig", newline="") as f:
        answers = list(csv.DictReader(f))

    rows = []
    for a in answers:
        q = questions[a["id"]]
        rows.append({
            **a,
            "answerable": q["answerable"],
            "expected_sources": " ; ".join(" OR ".join(g) for g in q["expected_source_groups"]),
            "double_annotation": q["double_annotation"],
        })

    stem = answers_path.with_suffix("")
    grid_a = Path(f"{stem}-grid-A.xlsx")
    grid_b = Path(f"{stem}-grid-B.xlsx")
    build(rows, grid_a, "annotateur_A")
    build([r for r in rows if r["double_annotation"]], grid_b, "annotateur_B")
    print(f"Wrote {grid_a} ({len(rows)} rows)")
    print(f"Wrote {grid_b} ({sum(r['double_annotation'] for r in rows)} rows)")


if __name__ == "__main__":
    main()
