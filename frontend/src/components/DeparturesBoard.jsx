import { useEffect, useState } from "react";
import { ExternalLink, RotateCw } from "lucide-react";
import { AVIONIO_CONFIG } from "../config/avionio";

export default function DeparturesBoard() {
  const [loading, setLoading] = useState(AVIONIO_CONFIG.enabled);
  const [error, setError] = useState(!AVIONIO_CONFIG.enabled);
  const [iframeKey, setIframeKey] = useState(0);

  useEffect(() => {
    if (!AVIONIO_CONFIG.enabled || !loading) return undefined;
    const timeout = window.setTimeout(() => {
      setLoading(false);
      setError(true);
    }, 12000);
    return () => window.clearTimeout(timeout);
  }, [iframeKey, loading]);

  const reloadBoard = () => {
    if (!AVIONIO_CONFIG.enabled) return;
    setError(false);
    setLoading(true);
    setIframeKey((current) => current + 1);
  };

  return (
    <section id="departures" className="departures-section" aria-labelledby="departures-title">
      <div className="departures-header">
        <div>
          <span className="section-label">FLIGHT INFORMATION</span>
          <h2 id="departures-title">Flight board</h2>
          <p>Departure information provided by an external flight board.</p>
        </div>
        {AVIONIO_CONFIG.enabled && (
          <div className="departures-actions">
            <span className="board-status">EXTERNAL BOARD</span>
            <a className="flight-board-external-link" href={AVIONIO_CONFIG.externalUrl} target="_blank" rel="noreferrer">
              Open externally <ExternalLink size={14} />
            </a>
            <button type="button" className="reload-button" onClick={reloadBoard} aria-label="Reload flight board">
              <RotateCw size={16} />
            </button>
          </div>
        )}
      </div>

      {!AVIONIO_CONFIG.enabled ? (
        <div className="departures-unavailable">
          <h3>Flight board unavailable</h3>
          <p>Live flight information is not configured. Please check with the airport or your airline.</p>
        </div>
      ) : (
        <div className="avionio-container">
          {loading && (
            <div className="avionio-loading" role="status">
              <div className="airport-loader" aria-hidden="true"><span className="loader-plane">✈</span></div>
              <p>Loading flight board…</p>
            </div>
          )}
          {error ? (
            <div className="avionio-error" role="status">
              <h3>Flight board could not be loaded</h3>
              <p>The external provider may be unavailable or block embedded pages.</p>
              <div className="flight-board-actions">
                <button type="button" onClick={reloadBoard}>Try again</button>
                <a href={AVIONIO_CONFIG.externalUrl} target="_blank" rel="noreferrer">
                  Open flight board <ExternalLink size={14} />
                </a>
                <a href={AVIONIO_CONFIG.officialUrl} target="_blank" rel="noreferrer">
                  Official ONDA flights <ExternalLink size={14} />
                </a>
              </div>
            </div>
          ) : (
            <iframe
              key={iframeKey}
              src={AVIONIO_CONFIG.iframeUrl}
              title="Agadir airport flight board"
              className="avionio-iframe"
              onLoad={() => { setLoading(false); setError(false); }}
              onError={() => { setLoading(false); setError(true); }}
              loading="lazy"
              referrerPolicy="strict-origin-when-cross-origin"
              allowFullScreen
            />
          )}
        </div>
      )}
      <p className="departures-note">Flight times and status can change. Confirm important information with your airline.</p>
    </section>
  );
}
