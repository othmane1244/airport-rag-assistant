import { useEffect, useState } from "react";
import keycloak from "./keycloak";
import { AuthContext } from "./AuthContext";

let initialization;
const localAuthBypass =
  import.meta.env.DEV && import.meta.env.VITE_AUTH_DISABLED?.toLowerCase() === "true";

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() =>
    localAuthBypass
      ? { ready: true, authenticated: true, error: null }
      : { ready: false, authenticated: false, error: null },
  );

  useEffect(() => {
    let mounted = true;

    if (localAuthBypass) return;

    initialization ||= keycloak.init({
      onLoad: "login-required",
      pkceMethod: "S256",
      checkLoginIframe: false,
      enableLogging: false,
    });

    initialization
      .then((authenticated) => {
        if (mounted) setAuth({ ready: true, authenticated, error: null });
      })
      .catch((error) => {
        console.error("Keycloak initialization failed", error);
        if (mounted) setAuth({ ready: true, authenticated: false, error });
      });

    return () => {
      mounted = false;
    };
  }, []);

  const value = {
    ...auth,
    username: localAuthBypass
      ? "Local preview"
      : keycloak.tokenParsed?.preferred_username || keycloak.tokenParsed?.name || "",
    isDocumentAdmin: !localAuthBypass
      && keycloak.tokenParsed?.realm_access?.roles?.includes("document-admin") === true,
    logout: localAuthBypass
      ? () => window.location.reload()
      : () => keycloak.logout({ redirectUri: window.location.origin }),
    retry: () => window.location.reload(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
