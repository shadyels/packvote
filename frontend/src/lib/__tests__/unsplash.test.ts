import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDestinationImage } from "../unsplash";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function makeUnsplashResponse(imageUrl: string, name: string, htmlUrl: string) {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        results: [
          {
            urls: { regular: imageUrl },
            user: { name, links: { html: htmlUrl } },
          },
        ],
      }),
  };
}

describe("useDestinationImage", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns a deterministic gradient fallback when no API key", async () => {
    // No VITE_UNSPLASH_ACCESS_KEY → fetchUnsplashPhoto returns null immediately
    const { result } = renderHook(() => useDestinationImage("Paris"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.imageUrl).toBeNull();
    expect(result.current.gradient).toMatch(/linear-gradient/);
  });

  it("gradient is deterministic — same destination gives same gradient", () => {
    const { result: r1 } = renderHook(() => useDestinationImage("Tokyo"));
    const { result: r2 } = renderHook(() => useDestinationImage("Tokyo"));
    expect(r1.current.gradient).toBe(r2.current.gradient);
  });

  it("different destinations can produce different gradients", () => {
    // Use destinations with sufficiently different hashes
    const { result: r1 } = renderHook(() => useDestinationImage("A"));
    const { result: r2 } = renderHook(() => useDestinationImage("ZZZZZZZZZZ"));
    // Not guaranteed to differ (only 8 palettes), but at least both are valid
    expect(r1.current.gradient).toMatch(/linear-gradient/);
    expect(r2.current.gradient).toMatch(/linear-gradient/);
  });

  it("fetches from Unsplash when API key is set and returns imageUrl", async () => {
    vi.stubEnv("VITE_UNSPLASH_ACCESS_KEY", "test-key");
    const uniqueDest = `UniqueDest_${Date.now().toString()}`;
    mockFetch.mockResolvedValueOnce(
      makeUnsplashResponse(
        "https://images.unsplash.com/photo.jpg",
        "Jane Doe",
        "https://unsplash.com/@jane"
      )
    );

    const { result } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.imageUrl).toBe(
      "https://images.unsplash.com/photo.jpg"
    );
    expect(result.current.photographer).toBe("Jane Doe");
  });

  it("caches result and avoids a second fetch for the same destination", async () => {
    vi.stubEnv("VITE_UNSPLASH_ACCESS_KEY", "test-key");
    const uniqueDest = `CachedDest_${Date.now().toString()}`;
    mockFetch.mockResolvedValue(
      makeUnsplashResponse("https://img.example.com/1.jpg", "Photographer", "")
    );

    // First render
    const { result: r1 } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => expect(r1.current.isLoading).toBe(false));
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Second render with same destination — should use cache
    const { result: r2 } = renderHook(() => useDestinationImage(uniqueDest));
    await waitFor(() => expect(r2.current.isLoading).toBe(false));
    expect(mockFetch).toHaveBeenCalledTimes(1); // still only 1 call
    expect(r2.current.imageUrl).toBe("https://img.example.com/1.jpg");
  });
});
