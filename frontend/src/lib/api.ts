import { API_URL } from "./constants";

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
      if (!res.ok) return false;
      return true;
    } catch {
      return false;
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

    let res = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
      credentials: "include",
    });

    if (res.status === 401) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        res = await fetch(`${this.baseUrl}${endpoint}`, {
          ...options,
          headers,
          credentials: "include",
        });
      } else {
        this.clearTokens();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        throw new Error("Session expired");
      }
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${res.status}`);
    }

    return res.json();
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
