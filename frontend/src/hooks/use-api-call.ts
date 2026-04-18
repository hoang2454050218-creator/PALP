"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

export type ApiCallStatus = "idle" | "loading" | "success" | "error";

export interface UseApiCallOptions {
  /** Title shown in the toast on failure. */
  errorTitle?: string;
  /** Whether to surface a toast on failure. */
  toastOnError?: boolean;
  /** Friendly fallback message if the error has no detail. */
  fallbackMessage?: string;
  /** Treat 404 as empty data (no toast, no error). */
  treat404AsEmpty?: boolean;
}

const DEFAULT_OPTIONS: Required<Omit<UseApiCallOptions, "errorTitle" | "fallbackMessage">> = {
  toastOnError: true,
  treat404AsEmpty: false,
};

/**
 * Centralised data-fetch hook so every page reacts the same way to errors:
 *   - normalises the thrown value into `ApiError`
 *   - surfaces a toast (unless caller opts out)
 *   - exposes `status`, `error`, `data` for inline UI states
 *   - guards against state updates after unmount (avoids React warnings).
 *
 * Usage:
 *   const { data, status, error, run } = useApiCall<MasteryState[]>();
 *   useEffect(() => { run(() => api.get("/adaptive/mastery/")); }, []);
 */
export function useApiCall<T>(options: UseApiCallOptions = {}) {
  const { toastOnError, treat404AsEmpty } = { ...DEFAULT_OPTIONS, ...options };
  const errorTitle = options.errorTitle ?? "Đã xảy ra lỗi";
  const fallbackMessage = options.fallbackMessage ?? "Vui lòng thử lại sau ít phút.";

  const [status, setStatus] = useState<ApiCallStatus>("idle");
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const run = useCallback(
    async (fetcher: () => Promise<T>): Promise<T | null> => {
      setStatus("loading");
      setError(null);
      try {
        const result = await fetcher();
        if (!mountedRef.current) return result;
        setData(result);
        setStatus("success");
        return result;
      } catch (raw) {
        if (!mountedRef.current) return null;
        const err = raw instanceof ApiError
          ? raw
          : new ApiError({ status: 0, detail: String(raw ?? fallbackMessage) });

        if (treat404AsEmpty && err.isNotFound()) {
          setData(null);
          setStatus("success");
          return null;
        }

        setError(err);
        setStatus("error");
        if (toastOnError && !err.isUnauthorized()) {
          toast({
            variant: "error",
            title: errorTitle,
            description: err.detail || fallbackMessage,
          });
        }
        return null;
      }
    },
    [errorTitle, fallbackMessage, toastOnError, treat404AsEmpty],
  );

  const reset = useCallback(() => {
    setStatus("idle");
    setData(null);
    setError(null);
  }, []);

  return { status, data, error, run, reset, setData };
}
