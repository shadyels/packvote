import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDestinationImage } from "../unsplash";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function makeBackendResponse(imageUrls: string[]) {
  return {
    ok: true,
    json: () => Promise.resolve({ images: imageUrls }),
  };
}

describe("useDestinationImage", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("gradient is deterministic — same destination gives same gradient", () => {
    const { result: r1 } = renderHook(() => useDestinationImage("Tokyo"));
    const { result: r2 } = renderHook(() => useDestinationImage("Tokyo"));
    expect(r1.current.gradient).toBe(r2.current.gradient);
  });

  it("different destinations can produce different gradients", () => {
    const { result: r1 } = renderHook(() => useDestinationImage("A"));
    const { result: r2 } = renderHook(() => useDestinationImage("ZZZZZZZZZZ"));
    expect(r1.current.gradient).toMatch(/linear-gradient/);
    expect(r2.current.gradient).toMatch(/linear-gradient/);
  });

  it("fetches from backend and returns imageUrl", async () => {
    const uniqueDest = `UniqueDest_${Date.now().toString()}`;
    mockFetch.mockResolvedValueOnce(
      makeBackendResponse(["https://images.unsplash.com/photo.jpg"])
    );

    const { result } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.imageUrl).toBe("https://images.unsplash.com/photo.jpg");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/unsplash/photo?destination=")
    );
  });

  it("caches result and avoids a second fetch for the same destination", async () => {
    const uniqueDest = `CachedDest_${Date.now().toString()}`;
    mockFetch.mockResolvedValue(
      makeBackendResponse(["https://img.example.com/1.jpg"])
    );

    const { result: r1 } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => {
      expect(r1.current.isLoading).toBe(false);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);

    const { result: r2 } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => {
      expect(r2.current.isLoading).toBe(false);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1); // still 1
    expect(r2.current.imageUrl).toBe("https://img.example.com/1.jpg");
  });

  it("backend returns empty images → null imageUrl + gradient fallback", async () => {
    const uniqueDest = `EmptyDest_${Date.now().toString()}`;
    mockFetch.mockResolvedValueOnce(makeBackendResponse([]));

    const { result } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.imageUrl).toBeNull();
    expect(result.current.gradient).toMatch(/linear-gradient/);
  });

  it("backend rate-limit (empty images) → null imageUrl + gradient fallback", async () => {
    // Same code path as empty images — backend returns {images: []} when over limit
    const uniqueDest = `RateLimitedDest_${Date.now().toString()}`;
    mockFetch.mockResolvedValueOnce(makeBackendResponse([]));

    const { result } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.imageUrl).toBeNull();
    expect(result.current.gradient).toMatch(/linear-gradient/);
  });

  it("backend error → null imageUrl + gradient fallback", async () => {
    const uniqueDest = `ErrorDest_${Date.now().toString()}`;
    mockFetch.mockResolvedValueOnce({ ok: false, json: () => Promise.resolve({}) });

    const { result } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.imageUrl).toBeNull();
    expect(result.current.gradient).toMatch(/linear-gradient/);
  });
});
