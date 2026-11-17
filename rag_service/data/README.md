# Source documents

This folder holds the PDF documents the assistant retrieves from. **None are included in the
repository**: the documents used during development belong to the airport operator and are not
redistributed here. `rag_service/data/pdfs/` is ignored by Git, and so are the vector index
(`backend/chroma_data/`) and its backups.

## Using your own documents

1. Put your own PDFs (documents you have the right to use) in `rag_service/data/pdfs/`.
   The folder is bind-mounted into the `rag` container by `docker-compose.yml`.
2. Start the stack (`docker compose up --build`), then index the documents from the `rag`
   container. A dry run first prints the extraction and deduplication report without writing:

   ```bash
   docker compose exec rag python scripts/batch_ingest_pdfs.py --dry-run --audience voyageur
   docker compose exec rag python scripts/batch_ingest_pdfs.py --audience voyageur
   ```

3. Documents can also be uploaded from the admin panel by a user with the `document-admin` role.

The `audience` tag (`voyageur`, `professionnel`, `interne_gouvernance`, `a_qualifier`) controls
what passengers can retrieve. Without any indexed document, the assistant has nothing to answer
from.
