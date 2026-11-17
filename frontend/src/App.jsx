import Home from "./pages/Home";
import { AuthProvider } from "./auth/AuthProvider";
import { useAuth } from "./auth/useAuth";

function AuthenticatedApp() {
  const { ready, authenticated, error, retry } = useAuth();

  if (!ready || !authenticated) {
    return (
      <main className="auth-status" role="status" aria-live="polite" aria-busy={!ready}>
        <div className={`auth-status-card ${error ? "auth-status-error" : "auth-status-loading"}`}>
          <strong>{error ? "Connexion indisponible" : "Connexion sécurisée…"}</strong>
          <p>
            {error
              ? "Keycloak ne répond pas. Vérifiez qu’il est démarré, puis réessayez."
              : "Redirection vers la page de connexion Keycloak…"}
          </p>
          {error && <button type="button" onClick={retry}>Réessayer</button>}
        </div>
      </main>
    );
  }

  return <Home />;
}

export default function App() {
  return (
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}
