# Backend services

The backend is split into two independently runnable FastAPI services:

| Service | Responsibility | Local URL |
| --- | --- | --- |
| `api_service` | Public chat API, flight lookup, Gemini and Groq response generation | `http://127.0.0.1:8001` |
| `../rag_service` | Knowledge retrieval, Chroma, embeddings, PDF ingestion | `http://127.0.0.1:8002` |

The API calls the RAG service over HTTP. Only the API service should be exposed to the frontend. Keep the RAG service on a private network in deployments.

## Run locally

Create a virtual environment and install each service's dependencies separately.

```powershell
cd rag_service
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8002
```

In a second terminal:

```powershell
cd backend/api_service
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8001
```

The frontend can use `http://127.0.0.1:8001` as `VITE_API_URL`. Configure external provider keys in `backend/api_service/.env`; configure the Chroma path, offline embedder mode, and optional Mistral OCR key in `rag_service/.env`.

## RAG ingestion

Run ingestion commands from `rag_service`:

```powershell
python scripts/batch_ingest_pdfs.py --audience voyageur --dry-run
python scripts/batch_ingest_pdfs.py --audience voyageur
```

Use a real embedding model for production ingestion and retrieval. The deterministic offline embedder only checks plumbing and does not perform semantic search. Tag PDFs by audience before indexing; public chat queries only the `voyageur` audience from the PDF collection. This service uses the PDF collection as its knowledge source; the old unverified JSON examples are archived under the workspace `draft/` directory.

## Document administration

An authenticated account with the Keycloak realm role `document-admin` can
manage the knowledge base from the **Documents** panel in the airport UI. It
supports listing indexed PDFs, uploading/replacing a PDF (20 MB and 500 pages
maximum), and removing a document from both the index and the mounted PDF
directory. Uploads are indexed for the `voyageur` audience. Scanned PDFs are
rejected when they contain no extractable text; the upload path deliberately
does not call paid Mistral OCR.

The API exposes `GET`, `POST` and `DELETE /admin/documents`; each checks the
`document-admin` role before proxying to the private RAG service. The RAG service
must stay on its internal Docker network. The Compose PDF directory is writable
so documents survive container recreation. To grant access in an existing
Keycloak realm, create the `document-admin` realm role and assign it to the
chosen user in the Admin Console, then sign that user out and back in.

Before changing embeddings, chunking, or adding a reranker, run `python scripts/evaluate_retrieval.py` from `rag_service` while the RAG service is running. It reports Hit@3, MRR@5, and retrieval latency for representative airport questions so quality and speed changes can be compared against the current index.

The expanded draft benchmark can be run in both retrieval variants from `rag_service`:

```bash
python scripts/evaluate_retrieval.py --dataset evaluation/benchmark_v2_150.json
python scripts/evaluate_retrieval.py --dataset evaluation/benchmark_v2_150.json --query-expansion
```

It contains 150 questions across French, English and Arabic. Scores cover retrieval only; the unanswerable cases report candidate-retrieval diagnostics and do not grade chatbot abstention. Review the expected sources and translations with an airport-domain expert before using the results as formal evidence.

## Identity and local development

The API validates Keycloak bearer tokens on chat routes. For a local preview without Docker/Keycloak, set `AUTH_DISABLED=true` in `backend/api_service/.env`; this bypass is accepted only while `ENVIRONMENT=development`. Never set it in a deployed environment. The frontend local preview also accepts `VITE_AUTH_DISABLED=true` in `frontend/.env.local`.

The RAG service is an internal dependency and should not be exposed publicly. It warms BGE-M3 before its health check succeeds so the first chat request does not time out during model loading. If the model is already cached locally but Hugging Face is unreachable, set `RAG_LOCAL_FILES_ONLY=true` in `rag_service/.env`.

## Health, readiness, and API docs

- API: `GET /health` checks that the API process responds; `GET /ready` checks the API-to-RAG connection. Docs at `/docs` are development-only.
- RAG: `GET /health`, `POST /query`, docs at `/docs`

The Compose API health check uses `/ready`, so the frontend waits for both the
API and its RAG dependency. Chat requests still use Keycloak authentication;
the local development bypass is not used by Compose.

Each service owns its requirements file and configuration. Chroma persistence defaults to the existing `backend/chroma_data` directory so the existing index remains available after the move; set `CHROMA_PERSIST_DIR` to a mounted persistent volume in deployment.
