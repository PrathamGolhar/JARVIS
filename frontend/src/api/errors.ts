export type ApiErrorCategory =
  | "NETWORK_ERROR"
  | "BACKEND_UNAVAILABLE"
  | "HTTP_400"
  | "HTTP_401"
  | "HTTP_403"
  | "HTTP_404"
  | "HTTP_429"
  | "HTTP_500"
  | "TIMEOUT"
  | "AI_PROVIDER_ERROR"
  | "TTS_ERROR"
  | "WEB_SEARCH_ERROR"
  | "INVALID_RESPONSE";

export interface StructuredApiErrorDetails {
  category: ApiErrorCategory;
  message: string;
  statusCode?: number;
  endpoint?: string;
  provider?: string;
  requestId?: string;
  isRetryable?: boolean;
}

export class JarvisApiError extends Error {
  public category: ApiErrorCategory;
  public statusCode?: number;
  public endpoint?: string;
  public provider?: string;
  public requestId?: string;
  public isRetryable: boolean;

  constructor(details: StructuredApiErrorDetails) {
    super(details.message);
    this.name = "JarvisApiError";
    this.category = details.category;
    this.statusCode = details.statusCode;
    this.endpoint = details.endpoint;
    this.provider = details.provider;
    this.requestId = details.requestId;
    this.isRetryable = details.isRetryable ?? false;
  }
}

/**
 * Categorize a raw error or HTTP response into a safe, structured API error.
 * Strips any authorization headers, secret keys, or sensitive internal tokens.
 */
export async function parseApiError(
  errOrResponse: unknown,
  endpoint?: string
): Promise<JarvisApiError> {
  if (errOrResponse instanceof JarvisApiError) {
    return errOrResponse;
  }

  // Handle Response objects
  if (errOrResponse instanceof Response) {
    const status = errOrResponse.status;
    let detail = "";
    try {
      const body = await errOrResponse.json();
      detail = body.detail || body.message || body.error || "";
    } catch {
      // Body not JSON
    }

    if (status === 401) {
      return new JarvisApiError({
        category: "HTTP_401",
        statusCode: 401,
        endpoint,
        message: detail || "Authentication required or invalid API key.",
        isRetryable: false,
      });
    }

    if (status === 403) {
      return new JarvisApiError({
        category: "HTTP_403",
        statusCode: 403,
        endpoint,
        message: detail || "Operation forbidden or upstream service permission denied.",
        isRetryable: false,
      });
    }

    if (status === 404) {
      return new JarvisApiError({
        category: "HTTP_404",
        statusCode: 404,
        endpoint,
        message: detail || `Requested endpoint not found: ${endpoint || ""}`,
        isRetryable: false,
      });
    }

    if (status === 429) {
      return new JarvisApiError({
        category: "HTTP_429",
        statusCode: 429,
        endpoint,
        message: detail || "Service rate limit reached. Please wait a moment before trying again.",
        isRetryable: true,
      });
    }

    if (status >= 500) {
      return new JarvisApiError({
        category: "HTTP_500",
        statusCode: status,
        endpoint,
        message: detail || `Server returned an error (HTTP ${status}).`,
        isRetryable: status === 502 || status === 503 || status === 504,
      });
    }

    return new JarvisApiError({
      category: "HTTP_400",
      statusCode: status,
      endpoint,
      message: detail || `Request failed with HTTP ${status}.`,
      isRetryable: false,
    });
  }

  // Handle network / fetch failures (e.g., TypeError: Failed to fetch)
  if (errOrResponse instanceof Error) {
    if (errOrResponse.name === "AbortError") {
      return new JarvisApiError({
        category: "TIMEOUT",
        endpoint,
        message: "The request timed out. Please check your network and try again.",
        isRetryable: true,
      });
    }

    const msg = errOrResponse.message.toLowerCase();
    if (msg.includes("failed to fetch") || msg.includes("networkerror") || msg.includes("econnrefused")) {
      return new JarvisApiError({
        category: "BACKEND_UNAVAILABLE",
        endpoint,
        message: "JARVIS backend service is unreachable. Ensure the FastAPI server is running on port 8765.",
        isRetryable: true,
      });
    }

    return new JarvisApiError({
      category: "NETWORK_ERROR",
      endpoint,
      message: errOrResponse.message || "An unexpected network error occurred.",
      isRetryable: true,
    });
  }

  return new JarvisApiError({
    category: "INVALID_RESPONSE",
    endpoint,
    message: "Unknown error occurred while contacting the server.",
  });
}
