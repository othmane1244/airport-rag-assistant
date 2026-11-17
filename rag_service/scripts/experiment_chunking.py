"""Chunk-size experiment: 800/150 vs 1200/150 characters, in separate Chroma
collections. The main index (backend/chroma_data) is never opened for writing.

Scope: the passenger-facing search filters on audience "voyageur"; in the main
index that audience covered 50 PDFs (73 passages). The list comes from
evaluation/chunking/main_index_sources.json, a local file built from your own
index ({file: {"audience": ..., "passages": ...}}); it is not published, since it
names the source documents. Both collections are rebuilt
from these PDFs as ONE batch, with the same pipeline as
batch_ingest_pdfs.py (extraction -> cross-file dedup -> tables + article /
generic chunks), Mistral OCR disabled. Only chunk_generic's max_chars changes.

Retrieval is then evaluated on benchmark v2 with the service's behaviour:
query expansion on, top-5, no topic filter, no reranker (config B).

Usage (GPU optional):
    python scripts/experiment_chunking.py
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import chromadb  # noqa: E402

from app.rag import pdf_loader  # noqa: E402
from app.rag.dedup import deduplicate_batch  # noqa: E402
from app.rag.embeddings import get_embedder  # noqa: E402
from app.routers.query import _expand_domain_query  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
import batch_ingest_pdfs  # noqa: E402
from evaluate_retrieval import _group_ranks, _source_groups  # noqa: E402

EXP_DIR = ROOT / "evaluation" / "chunking"
PERSIST = EXP_DIR / "chroma_data"  # ignored by .gitignore
SIZES = (1200, 800)
OVERLAP = 150
AUDIENCE = "voyageur"
TOP_K = 5


def extract(paths: list[Path]) -> tuple[dict, dict]:
    texts, tables = {}, {}
    for p in paths:
        texts[p.name] = pdf_loader.extract_text_auto(p, mistral_api_key="")
        tables[p.name] = pdf_loader.extract_tables_from_pdf(p)
    return texts, tables


def build_docs(cleaned: dict, tables: dict, max_chars: int) -> list[dict]:
    original = pdf_loader.chunk_generic
    # batch_ingest_pdfs imported chunk_generic by name: patch it there.
    batch_ingest_pdfs.chunk_generic = lambda text: original(text, max_chars=max_chars, overlap=OVERLAP)
    try:
        docs = []
        for filename, text in cleaned.items():
            prefix = batch_ingest_pdfs.slugify(Path(filename).stem)
            base = {"type": "pdf", "source_file": filename, "audience": AUDIENCE}
            for t_idx, table in enumerate(tables[filename]):
                for r_idx, row_text in enumerate(pdf_loader._table_rows_to_texts(table["rows"])):
                    docs.append({"id": f"{prefix}_table{t_idx:02d}_row{r_idx:03d}", "text": row_text,
                                 "metadata": {**base, "heading": f"Tableau page {table['page']}, ligne {r_idx + 1}",
                                              "content_kind": "table_row"}})
            docs.extend(batch_ingest_pdfs.build_documents_from_cleaned_text(text, prefix, base))
        return docs
    finally:
        batch_ingest_pdfs.chunk_generic = original


def evaluate(collection, embedder, cases: list[dict]) -> dict:
    rows = []
    for case in cases:
        q = _expand_domain_query(case["query"])
        t0 = time.perf_counter()
        vec = embedder.embed([q])
        res = collection.query(query_embeddings=vec, n_results=TOP_K, where={"audience": AUDIENCE})
        latency = (time.perf_counter() - t0) * 1000
        results = [{"metadata": m} for m in res["metadatas"][0]]
        ranks = _group_ranks(results, _source_groups(case))
        found = [r for r in ranks if r is not None]
        rows.append({"id": case["id"], "lang": case["lang"], "answerable": case["answerable"],
                     "expected_rank": min(found) if found else None, "expected_group_ranks": ranks,
                     "latency_ms": latency})

    def summ(rs):
        ans = [r for r in rs if r["answerable"]]
        groups = [g for r in ans for g in r["expected_group_ranks"]]
        return {
            "answerable_questions": len(ans),
            "hit_at_3": sum(r["expected_rank"] is not None and r["expected_rank"] <= 3 for r in ans) / len(ans),
            "mrr_at_5": sum(1 / r["expected_rank"] for r in ans if r["expected_rank"]) / len(ans),
            "required_source_recall_at_5": sum(g is not None for g in groups) / len(groups),
            "median_latency_ms": round(statistics.median(r["latency_ms"] for r in rs), 1),
        }

    return {"metrics": summ(rows), "by_language": {l: summ([r for r in rows if r["lang"] == l]) for l in ("fr", "en", "ar")},
            "cases": rows}


def main() -> None:
    sources_file = EXP_DIR / "main_index_sources.json"
    if not sources_file.exists():
        raise SystemExit(f"{sources_file} not found: build it from your own index (see the module docstring).")
    sources = json.loads(sources_file.read_text(encoding="utf-8"))
    files = sorted(f for f, v in sources.items() if v["audience"] == AUDIENCE)
    paths = [ROOT / "data" / "pdfs" / f for f in files]
    print(f"{len(paths)} '{AUDIENCE}' PDFs; main index holds {sum(sources[f]['passages'] for f in files)} passages for them")

    t0 = time.perf_counter()
    texts, tables = extract(paths)
    cleaned, _ = deduplicate_batch(texts)
    print(f"extraction + dedup: {time.perf_counter() - t0:.0f} s")

    embedder = get_embedder(offline_test_mode=False, local_files_only=True)
    cases = json.loads((ROOT / "evaluation" / "benchmark_v2_150.json").read_text(encoding="utf-8"))["cases"]
    client = chromadb.PersistentClient(path=str(PERSIST))
    report = {"run_at_utc": datetime.now(timezone.utc).isoformat(), "audience": AUDIENCE, "pdfs": len(paths),
              "overlap": OVERLAP, "query_expansion": True, "top_k": TOP_K, "mistral_ocr": False,
              "main_index_passages_for_these_pdfs": sum(sources[f]["passages"] for f in files), "sizes": {}}
    for size in SIZES:
        docs = build_docs(cleaned, tables, size)
        name = f"exp_chunk_{size}_{OVERLAP}"
        try:
            client.delete_collection(name)
        except Exception:
            pass
        col = client.create_collection(name)  # same default distance as the main collection
        col.add(ids=[d["id"] for d in docs], documents=[d["text"] for d in docs],
                metadatas=[d["metadata"] for d in docs], embeddings=embedder.embed([d["text"] for d in docs]))
        lengths = [len(d["text"]) for d in docs]
        result = evaluate(col, embedder, cases)
        report["sizes"][str(size)] = {"collection": name, "passages": len(docs),
                                      "mean_passage_chars": round(statistics.mean(lengths)),
                                      "max_passage_chars": max(lengths), **result}
        m = result["metrics"]
        print(f"{size}/{OVERLAP}: {len(docs)} passages | Hit@3 {m['hit_at_3']:.3f} | MRR@5 {m['mrr_at_5']:.3f} | recall@5 {m['required_source_recall_at_5']:.3f}")

    out = ROOT / "evaluation" / "results" / "pipeline" / f"chunking-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
