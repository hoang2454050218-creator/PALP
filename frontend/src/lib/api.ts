import { API_URL } from "./constants";

/**
 * Structured API error returned by every non-2xx response. Components catch
 * `ApiError` (instead of bare Error) so they can branch on `status` (e.g. show
 * a friendly "Bài đánh giá đã hết hạn" for 410, or auto-retry idempotent 5xx)
 * and surface field-level validation back to forms via `fieldErrors`.
 */
export class ApiError extends Error {
  status: number;
  code: string | null;
  detail: string;
  fieldErrors: Record<string, string[]>;
  payload: unknown;

  constructor(opts: {
    status: number;
    detail: string;
    code?: string | null;
    fieldErrors?: Record<string, string[]>;
    payload?: unknown;
  }) {
    super(opts.detail);
    this.name = "ApiError";
    this.status = opts.status;
    this.code = opts.code ?? null;
    this.detail = opts.detail;
    this.fieldErrors = opts.fieldErrors ?? {};
    this.payload = opts.payload;
  }

  isUnauthorized() {
    return this.status === 401;
  }

  isForbidden() {
    return this.status === 403;
  }

  isNotFound() {
    return this.status === 404;
  }

  isServerError() {
    return this.status >= 500;
  }

  isNetwork() {
    return this.status === 0;
  }
}

const RETRY_ATTEMPTS = 2;
const RETRY_DELAY_MS = [400, 1200];
const RETRYABLE_STATUSES = new Set([0, 502, 503, 504]);

function isIdempotent(method: string | undefined): boolean {
  if (!method) return true;
  return ["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase());
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });
}

function normalizeError(status: number, body: unknown): ApiError {
  if (body && typeof body === "object") {
    const data = body as Record<string, unknown>;
    const detail = typeof data.detail === "string"
      ? data.detail
      : typeof data.message === "string"
        ? data.message
        : `API Error ${status}`;
    const code = typeof data.code === "string" ? data.code : null;
    const fieldErrors: Record<string, string[]> = {};
    for (const [k, v] of Object.entries(data)) {
      if (k === "detail" || k === "message" || k === "code") continue;
      if (Array.isArray(v)) {
        fieldErrors[k] = v.filter((item): item is string => typeof item === "string");
      }
    }
    return new ApiError({ status, detail, code, fieldErrors, payload: data });
  }
  return new ApiError({
    status,
    detail: typeof body === "string" && body ? body : `API Error ${status}`,
    payload: body,
  });
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_URL;
  }

  clearTokens() {
    if (typeof window === "undefined") return;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  }

  private async refreshAccessToken(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/auth/token/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({}),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  private redirectToLogin() {
    if (typeof window === "undefined") return;
    if (window.location.pathname === "/login") return;
    window.location.href = "/login";
  }

  private async fetchOnce(endpoint: string, options: RequestInit, headers: Record<string, string>) {
    try {
      return await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
        credentials: "include",
      });
    } catch (err) {
      // Network-level failure (CORS, offline). Surface as ApiError 0 so
      // callers can react uniformly instead of catching raw TypeError.
      throw new ApiError({
        status: 0,
        detail: "Không thể kết nối tới máy chủ.",
        code: "network_error",
        payload: err,
      });
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    const method = options.method ?? "GET";
    const retryable = isIdempotent(method);

    let lastError: ApiError | null = null;
    const maxAttempts = retryable ? RETRY_ATTEMPTS + 1 : 1;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        let res = await this.fetchOnce(endpoint, options, headers);

        if (res.status === 401) {
          const refreshed = await this.refreshAccessToken();
          if (refreshed) {
            res = await this.fetchOnce(endpoint, options, headers);
          } else {
            this.clearTokens();
            this.redirectToLogin();
            throw new ApiError({
              status: 401,
              detail: "Phiên đăng nhập đã hết hạn.",
              code: "session_expired",
            });
          }
        }

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw normalizeError(res.status, body);
        }

        if (res.status === 204) {
          return undefined as T;
        }
        return (await res.json()) as T;
      } catch (err) {
        if (!(err instanceof ApiError)) {
          throw err;
        }
        lastError = err;
        const shouldRetry =
          retryable &&
          attempt < maxAttempts - 1 &&
          RETRYABLE_STATUSES.has(err.status);
        if (shouldRetry) {
          await sleep(RETRY_DELAY_MS[Math.min(attempt, RETRY_DELAY_MS.length - 1)]);
          continue;
        }
        throw err;
      }
    }
    throw lastError ?? new ApiError({ status: 0, detail: "Unknown error" });
  }

  get<T>(endpoint: string) {
    return this.request<T>(endpoint);
  }

  post<T>(endpoint: string, body?: unknown) {
    return this.request<T>(endpoint, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(endpoint: string, body?: unknown) {
    return this.request<T>(endpoint, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  put<T>(endpoint: string, body?: unknown) {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  delete<T>(endpoint: string) {
    return this.request<T>(endpoint, {
      method: "DELETE",
    });
  }

  async login(username: string, password: string) {
    const data = await this.request<{ access: string; refresh: string }>(
      "/auth/login/",
      {
        method: "POST",
        body: JSON.stringify({ username, password }),
      },
    );
    return data;
  }

  async logout() {
    try {
      await this.request("/auth/logout/", { method: "POST" });
    } catch {
      // Best-effort server logout
    }
    this.clearTokens();
  }
}

export const api = new ApiClient();
