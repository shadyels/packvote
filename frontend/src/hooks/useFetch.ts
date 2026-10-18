import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";

interface FetchOptions<T> {
  /** Re-run the fetcher every N ms while `pollWhile(data)` holds. */
  pollMs?: number;
  /** Polling continues only while this returns true for the current data. Default: always. */
  pollWhile?: (data: T) => boolean;
}

interface FetchResult<T> {
  data: T | null;
  error: string | null;
  /** True only until the first successful load (no data yet). */
  isLoading: boolean;
  refetch: () => void;
}

export function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList,
  { pollMs, pollWhile }: FetchOptions<T> = {}
): FetchResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [tick, setTick] = useState(0);

  // Always call the latest closures without re-running the effect on every render.
  const fetcherRef = useRef(fetcher);
  const pollWhileRef = useRef(pollWhile);
  fetcherRef.current = fetcher;
  pollWhileRef.current = pollWhile;

  const requestId = useRef(0);
  const hasData = useRef(false);

  const refetch = useCallback(() => {
    setTick((t) => t + 1);
  }, []);

  const lastDeps = useRef<DependencyList | null>(null);

  useEffect(() => {
    // New deps mean a different resource: forget old data and show the loading state again.
    const prev = lastDeps.current;
    if (!prev || prev.length !== deps.length || prev.some((d, i) => !Object.is(d, deps[i]))) {
      hasData.current = false;
    }
    lastDeps.current = deps;

    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const id = ++requestId.current;

    const run = () => {
      if (!hasData.current) {
        setIsLoading(true);
        setData(null);
        setError(null);
      }
      fetcherRef
        .current()
        .then((result) => {
          if (!active || id !== requestId.current) return;
          hasData.current = true;
          setData(result);
          setError(null);
          setIsLoading(false);
          if (pollMs && (pollWhileRef.current?.(result) ?? true)) {
            timer = setTimeout(run, pollMs);
          }
        })
        .catch((err: unknown) => {
          if (!active || id !== requestId.current) return;
          setError(err instanceof Error ? err.message : "Something went wrong");
          setIsLoading(false);
          // A failed poll keeps the last data and tries again next interval.
          if (pollMs && hasData.current) timer = setTimeout(run, pollMs);
        });
    };
    run();

    return () => {
      active = false;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- caller-provided deps
  }, [...deps, tick, pollMs]);

  return { data, error, isLoading, refetch };
}
