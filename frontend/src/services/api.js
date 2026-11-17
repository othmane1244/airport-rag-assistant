import axios from "axios";
import keycloak from "../auth/keycloak";

const API_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8001"
).replace(/\/+$/, "");

const localAuthBypass =
  import.meta.env.DEV && import.meta.env.VITE_AUTH_DISABLED?.toLowerCase() === "true";
const REAUTH_MARKER = "aga-auth-redirect-started";

function reauthenticate() {
  if (localAuthBypass || !keycloak.authenticated) return;

  try {
    if (sessionStorage.getItem(REAUTH_MARKER)) return;
    sessionStorage.setItem(REAUTH_MARKER, "true");
  } catch {
    // Storage can be unavailable in privacy-restricted browser contexts.
  }

  keycloak.login({ redirectUri: window.location.href }).catch(() => {
    try {
      sessionStorage.removeItem(REAUTH_MARKER);
    } catch {
      // Keep the original API error if session storage is unavailable.
    }
  });
}

const api = axios.create({
  baseURL: API_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(async (config) => {
  if (keycloak.authenticated) {
    try {
      await keycloak.updateToken(30);
    } catch (error) {
      reauthenticate();
      throw error;
    }
    config.headers.Authorization = `Bearer ${keycloak.token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    if (response.config.url?.replace(/^\//, "").startsWith("chat")) {
      try {
        sessionStorage.removeItem(REAUTH_MARKER);
      } catch {
        // Storage can be unavailable in privacy-restricted browser contexts.
      }
    }
    return response;
  },
  (error) => {
    if (error.config?.url?.replace(/^\//, "").startsWith("chat") && error.response?.status === 401) {
      reauthenticate();
    }
    return Promise.reject(error);
  },
);

export default api;

export async function getAdminDocuments() {
  const response = await api.get("/admin/documents");
  return response.data.documents;
}

export async function uploadAdminDocument(file) {
  const response = await api.post("/admin/documents", file, {
    params: { filename: file.name },
    headers: { "Content-Type": "application/pdf" },
  });
  return response.data;
}

export async function deleteAdminDocument(filename) {
  const response = await api.delete("/admin/documents", { params: { filename } });
  return response.data;
}
