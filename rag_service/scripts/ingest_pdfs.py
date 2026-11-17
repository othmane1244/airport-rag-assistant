"""Import source PDFs into the passenger-facing Chroma collection."""

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

import chromadb  # noqa: E402

from app.config import settings  # noqa: E402
from app.rag.embeddings import get_embedder  # noqa: E402
from app.rag.pdf_loader import pdf_to_documents  # noqa: E402

PDF_DIR = BACKEND_ROOT / "data" / "pdfs"
COLLECTION_NAME = "aga_documents"


def slugify(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def main(pdf_paths: list[Path], offline_test_mode: bool = False, audience: str = "a_qualifier") -> None:
    all_docs = []
    for path in pdf_paths:
        print(f"Extraction de {path.name}...")
        docs = pdf_to_documents(
            path,
            doc_id_prefix=slugify(path.stem),
            extra_metadata={"audience": audience},
            mistral_api_key=settings.mistral_api_key if not offline_test_mode else "",
        )
        print(f"  -> {len(docs)} chunks")
        all_docs.extend(docs)

    if not all_docs:
        print("Aucun PDF trouvé / aucun chunk généré. Rien à indexer.")
        return

    embedder = get_embedder(offline_test_mode=offline_test_mode)
    if offline_test_mode:
        print("Mode --offline-test : embedder factice (PAS de recherche sémantique réelle).")
    print("Calcul des embeddings...")
    vectors = embedder.embed([d["text"] for d in all_docs])

    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    batch_size = 1000
    total_docs = len(all_docs)
    ids = [d["id"] for d in all_docs]
    documents = [d["text"] for d in all_docs]
    metadatas = [d["metadata"] for d in all_docs]

    print(f"-> Indexation de {total_docs} chunks par lots de {batch_size} dans ChromaDB...")
    for i in range(0, total_docs, batch_size):
        end = i + batch_size
        collection.upsert(
            ids=ids[i:end],
            embeddings=vectors[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
        )

    print(f"-> {total_docs} chunks indexés dans la collection '{COLLECTION_NAME}'.")
    print(f"-> Total actuel dans cette collection : {collection.count()}.")
    print()
    print("Rappel : va vérifier le champ metadata['audience'] de chaque document")
    print("indexé (\"a_qualifier\" par défaut) et corrige-le manuellement selon le")
    print("cas (ex: 'interne_gouvernance', 'voyageur_douane', etc.) — c'est ce tag")
    print("que le routeur d'intention utilisera à l'étape 4 pour décider quand")
    print("interroger cette collection.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", help="Chemins de PDF spécifiques. Si omis, scanne data/pdfs/."
    )
    parser.add_argument("--offline-test", action="store_true")
    parser.add_argument(
        "--audience",
        default="a_qualifier",
        choices=["a_qualifier", "voyageur", "interne_gouvernance", "professionnel"],
        help="Audience à enregistrer dans metadata['audience'] pour les PDF ingérés.",
    )
    args = parser.parse_args()

    if args.paths:
        pdf_paths = [Path(p) for p in args.paths]
    else:
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        pdf_paths = sorted(PDF_DIR.glob("*.pdf"))
        if not pdf_paths:
            print(f"Aucun PDF dans {PDF_DIR}. Dépose tes fichiers ici, ou passe un chemin en argument.")

    main(pdf_paths, offline_test_mode=args.offline_test, audience=args.audience)
