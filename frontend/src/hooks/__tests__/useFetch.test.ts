import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useFetch } from "../useFetch";

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useFetch", () => {
  it("isLoading is true on first load, then data arrives", async () => {
    const fetcher = vi.fn().mockResolvedValue("a");
    const { result } = renderHook(() => useFetch(fetcher, []));
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeNull();

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.data).toBe("a");
    expect(result.current.error).toBeNull();
  });

  it("refetch keeps data without flashing isLoading", async () => {
    const second = deferred<string>();
    const fetcher = vi.fn().mockResolvedValueOnce("a").mockReturnValueOnce(second.promise);
    const { result } = renderHook(() => useFetch(fetcher, []));
    await waitFor(() => {
      expect(result.current.data).toBe("a");
    });

    act(() => {
      result.current.refetch();
    });
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBe("a");

    await act(async () => {
      second.resolve("b");
      await second.promise;
    });
    expect(result.current.data).toBe("b");
  });

  it("reports errors, keeps stale data on a failed refetch, and clears the error on success", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce("a")
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce("c");
    const { result } = renderHook(() => useFetch(fetcher, []));
    await waitFor(() => {
      expect(result.current.data).toBe("a");
    });

    act(() => {
      result.current.refetch();
    });
    await waitFor(() => {
      expect(result.current.error).toBe("boom");
    });
    expect(result.current.data).toBe("a");

    act(() => {
      result.current.refetch();
    });
    await waitFor(() => {
      expect(result.current.data).toBe("c");
    });
    expect(result.current.error).toBeNull();
  });

  it("surfaces an error on first load with no data", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("nope"));
    const { result } = renderHook(() => useFetch(fetcher, []));
    await waitFor(() => {
      expect(result.current.error).toBe("nope");
    });
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeNull();
  });

  it("ignores an out-of-order response from a superseded request", async () => {
    const slow = deferred<string>();
    const fast = deferred<string>();
    const fetcher = vi.fn((id: string) => (id === "1" ? slow.promise : fast.promise));
    const { result, rerender } = renderHook(({ id }) => useFetch(() => fetcher(id), [id]), {
      initialProps: { id: "1" },
    });

    rerender({ id: "2" });
    await act(async () => {
      fast.resolve("two");
      await fast.promise;
    });
    expect(result.current.data).toBe("two");

    await act(async () => {
      slow.resolve("one");
      await slow.promise;
    });
    expect(result.current.data).toBe("two");
  });

  it("does not update state after unmount", async () => {
    const d = deferred<string>();
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { unmount } = renderHook(() => useFetch(() => d.promise, []));
    unmount();
    await act(async () => {
      d.resolve("late");
      await d.promise;
    });
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  describe("polling", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });
    afterEach(() => {
      vi.useRealTimers();
    });

    it("polls while poll returns a delay and stops once it returns null", async () => {
      const fetcher = vi
        .fn<() => Promise<{ status: string }>>()
        .mockResolvedValueOnce({ status: "GENERATING" })
        .mockResolvedValueOnce({ status: "GENERATING" })
        .mockResolvedValueOnce({ status: "VOTING" })
        .mockResolvedValue({ status: "VOTING" });

      const { result } = renderHook(() =>
        useFetch(fetcher, [], { poll: (d) => (d.status === "GENERATING" ? 1000 : null) })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(fetcher).toHaveBeenCalledTimes(1);
      expect(result.current.isLoading).toBe(false);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });
      expect(fetcher).toHaveBeenCalledTimes(2);
      expect(result.current.isLoading).toBe(false);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });
      expect(fetcher).toHaveBeenCalledTimes(3);
      expect(result.current.data?.status).toBe("VOTING");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });
      expect(fetcher).toHaveBeenCalledTimes(3);
    });

    it("keeps polling after a failed poll and keeps the last data", async () => {
      const fetcher = vi
        .fn<() => Promise<string>>()
        .mockResolvedValueOnce("a")
        .mockRejectedValueOnce(new Error("blip"))
        .mockResolvedValue("b");
      const { result } = renderHook(() => useFetch(fetcher, [], { poll: () => 1000 }));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });
      expect(result.current.data).toBe("a");
      expect(result.current.error).toBe("blip");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });
      expect(result.current.data).toBe("b");
      expect(result.current.error).toBeNull();
    });

    it("takes the next delay from poll(data), so it changes with the data", async () => {
      const fetcher = vi
        .fn<() => Promise<number>>()
        .mockResolvedValueOnce(1000)
        .mockResolvedValueOnce(3000)
        .mockResolvedValue(3000);
      renderHook(() => useFetch(fetcher, [], { poll: (d) => d }));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(fetcher).toHaveBeenCalledTimes(1);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
      });
      expect(fetcher).toHaveBeenCalledTimes(2);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2999);
      });
      expect(fetcher).toHaveBeenCalledTimes(2);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1);
      });
      expect(fetcher).toHaveBeenCalledTimes(3);
    });

    it("does not poll when poll returns null", async () => {
      const fetcher = vi.fn<() => Promise<string>>().mockResolvedValue("a");
      renderHook(() => useFetch(fetcher, [], { poll: () => null }));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(60000);
      });
      expect(fetcher).toHaveBeenCalledTimes(1);
    });

    it("skips requests while the tab is hidden and resumes when visible", async () => {
      let hidden = true;
      Object.defineProperty(document, "hidden", { configurable: true, get: () => hidden });
      try {
        const fetcher = vi.fn<() => Promise<string>>().mockResolvedValue("a");
        renderHook(() => useFetch(fetcher, [], { poll: () => 1000 }));
        await act(async () => {
          await vi.advanceTimersByTimeAsync(0);
        });
        expect(fetcher).toHaveBeenCalledTimes(1);

        await act(async () => {
          await vi.advanceTimersByTimeAsync(5000);
        });
        expect(fetcher).toHaveBeenCalledTimes(1);

        hidden = false;
        await act(async () => {
          await vi.advanceTimersByTimeAsync(1000);
        });
        expect(fetcher).toHaveBeenCalledTimes(2);
      } finally {
        Reflect.deleteProperty(document, "hidden");
      }
    });
  });
});
