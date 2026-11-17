import { useCallback, useEffect, useState } from "react";
import { FilePlus2, FileText, RefreshCw, Trash2, UploadCloud } from "lucide-react";

import {
  deleteAdminDocument,
  getAdminDocuments,
  uploadAdminDocument,
} from "../services/api";
import "./DocumentAdmin.css";

function readableSize(bytes) {
  if (bytes == null) return "Fichier absent";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function errorMessage(error) {
  return error.response?.data?.detail || "Une erreur est survenue. Réessayez.";
}

export default function DocumentAdmin() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDocuments(await getAdminDocuments());
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Sélectionnez un fichier PDF.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await uploadAdminDocument(file);
      setNotice(`${result.filename} indexé : ${result.chunks} passages ajoutés.`);
      await refresh();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (document) => {
    if (!window.confirm(`Supprimer « ${document.filename} » de l’index et du stockage ?`)) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await deleteAdminDocument(document.filename);
      setNotice(`${document.filename} supprimé.`);
      await refresh();
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section id="document-admin" className="document-admin-section">
      <div className="document-admin-card">
        <div className="document-admin-heading">
          <div>
            <span className="document-admin-eyebrow">ESPACE ADMINISTRATEUR</span>
            <h2>Documents de connaissance</h2>
            <p>Ajoutez des PDF pour les indexer dans l’assistant, ou retirez les documents obsolètes.</p>
          </div>
          <FileText aria-hidden="true" size={28} />
        </div>

        <div className="document-admin-actions">
          <label className={`document-upload-button ${busy ? "is-disabled" : ""}`}>
            <UploadCloud size={18} />
            <span>{busy ? "Indexation en cours…" : "Ajouter un PDF"}</span>
            <input type="file" accept="application/pdf,.pdf" disabled={busy} onChange={handleUpload} />
          </label>
          <span className="document-upload-hint">PDF textuel, 20 Mo maximum · 500 pages maximum</span>
          <button type="button" className="document-refresh-button" onClick={refresh} disabled={loading || busy}>
            <RefreshCw size={16} className={loading ? "is-spinning" : ""} />
            Actualiser
          </button>
        </div>

        {error && <p className="document-admin-message is-error" role="alert">{error}</p>}
        {notice && <p className="document-admin-message is-success" role="status">{notice}</p>}

        <div className="document-table-wrap">
          <table className="document-table">
            <thead>
              <tr><th>Document</th><th>Passages indexés</th><th>Taille</th><th>Gestion</th><th><span className="sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="5" className="document-table-empty">Chargement de l’index…</td></tr>
              ) : documents.length === 0 ? (
                <tr><td colSpan="5" className="document-table-empty"><FilePlus2 size={18} /> Aucun document indexé</td></tr>
              ) : documents.map((document) => (
                <tr key={document.filename}>
                  <td className="document-name-cell"><FileText size={17} /><span title={document.filename}>{document.filename}</span></td>
                  <td>{document.chunks}</td>
                  <td>{readableSize(document.size_bytes)}</td>
                  <td>{document.managed_by_admin ? "Ajouté ici" : "Corpus initial"}</td>
                  <td className="document-delete-cell">
                    <button type="button" aria-label={`Supprimer ${document.filename}`} title="Supprimer" disabled={busy} onClick={() => handleDelete(document)}>
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
