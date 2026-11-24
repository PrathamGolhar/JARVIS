import { DEMO_MODE } from "../config/mode";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

// Local Vite development uses its proxy. A deployed frontend supplies this at
// build time, for example https://jarvis-api.example.com/api.
export const API_BASE_URL = configuredBaseUrl || "/api";
export { DEMO_MODE };

// In-memory credential storage
let activeSessionToken: string | null = null;
let activeApiKey: string | null = import.meta.env.VITE_JARVIS_API_KEY?.trim() || null;

// Attempt to restore token or api key from sessionStorage if available
try {
  if (typeof window !== "undefined" && window.sessionStorage) {
    activeSessionToken = window.sessionStorage.getItem("jarvis_session_token");
    if (!activeApiKey) {
      activeApiKey = window.sessionStorage.getItem("jarvis_api_key");
    }
  }
} catch {
  // Silent fallback for environments without sessionStorage
}

export function setSessionToken(token: string | null): void {
  activeSessionToken = token;
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      if (token) {
        window.sessionStorage.setItem("jarvis_session_token", token);
      } else {
        window.sessionStorage.removeItem("jarvis_session_token");
      }
    }
  } catch {
    // Ignore storage errors
  }
}

export function getSessionToken(): string | null {
  return activeSessionToken;
}

export function setApiKey(key: string | null): void {
  activeApiKey = key;
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      if (key) {
        window.sessionStorage.setItem("jarvis_api_key", key);
      } else {
        window.sessionStorage.removeItem("jarvis_api_key");
      }
    }
  } catch {
    // Ignore storage errors
  }
}

export function getApiKey(): string | null {
  return activeApiKey;
}

/**
 * Exchange an API key for a high-entropy session token with the backend.
 */
export async function authenticateSession(apiKey?: string): Promise<boolean> {
  const keyToUse = apiKey || activeApiKey;
  if (!keyToUse) return false;

  const originalFetch = (window as unknown as { __originalFetch?: typeof fetch }).__originalFetch || window.fetch.bind(window);
  try {
    const res = await originalFetch(`${API_BASE_URL}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: keyToUse }),
    });
    if (res.ok) {
      const data = (await res.json()) as { ok: boolean; session_token: string };
      if (data.session_token) {
        setSessionToken(data.session_token);
        if (apiKey) setApiKey(apiKey);
        return true;
      }
    }
  } catch (err) {
    console.warn("Failed to negotiate session token:", err);
  }
  return false;
}

/**
 * Centralized authenticated fetch wrapper that attaches Authorization / X-API-Key headers.
 */
export async function fetchWithAuth(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const originalFetch = (window as unknown as { __originalFetch?: typeof fetch }).__originalFetch || window.fetch.bind(window);
  const reqInit = init || {};
  const headers = new Headers(reqInit.headers || {});

  if (activeSessionToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${activeSessionToken}`);
  } else if (activeApiKey && !headers.has("X-API-Key")) {
    headers.set("X-API-Key", activeApiKey);
  }

  let response = await originalFetch(input, { ...reqInit, headers });

  // If 401 Unauthorized and an API key is known, attempt automatic session token negotiation
  if (response.status === 401 && activeApiKey && !(typeof input === "string" && input.includes("/auth/token"))) {
    const refreshed = await authenticateSession(activeApiKey);
    if (refreshed && activeSessionToken) {
      headers.set("Authorization", `Bearer ${activeSessionToken}`);
      response = await originalFetch(input, { ...reqInit, headers });
    }
  }

  return response;
}

// Preserve original fetch and install transparent auth interceptor for browser window
if (typeof window !== "undefined") {
  const win = window as unknown as { __originalFetch?: typeof fetch };
  if (!win.__originalFetch) {
    win.__originalFetch = window.fetch.bind(window);
    window.fetch = fetchWithAuth;
  }
}
