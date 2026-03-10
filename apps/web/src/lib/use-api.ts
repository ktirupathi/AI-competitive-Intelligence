"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseApiOptions {
  /** Number of automatic retries on failure (default 2). */
  retries?: number;
  /** Base delay in ms between retries — doubles each attempt (default 1000). */
  retryDelay?: number;
  /** If true, fetch is not triggered automatically on mount. */
  manual?: boolean;
}

interface UseApiResult<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** Manually trigger the fetch (useful with manual: true or for retry). */
  refetch: () => Promise<void>;
}

/**
 * Generic data-fetching hook with exponential-backoff retry.
 *
 * Usage:
 * ```tsx
 * const { data, error, loading, refetch } = useApi(() => getCompetitors());
 * ```
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  options: UseApiOptions = {}
): UseApiResult<T> {
  const { retries = 2, retryDelay = 1000, manual = false } = options;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!manual);

  // Keep the latest fetcher in a ref to avoid re-running effect on every render
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);

    let lastError: unknown = null;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const result = await fetcherRef.current();
        setData(result);
        setLoading(false);
        return;
      } catch (err) {
        lastError = err;
        if (attempt < retries) {
          await new Promise((r) => setTimeout(r, retryDelay * 2 ** attempt));
        }
      }
    }

    const message =
      lastError instanceof Error
        ? lastError.message
        : "An unexpected error occurred.";
    setError(message);
    setLoading(false);
  }, [retries, retryDelay]);

  useEffect(() => {
    if (!manual) {
      execute();
    }
  }, [manual, execute]);

  return { data, error, loading, refetch: execute };
}
