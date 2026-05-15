import { useState, useEffect } from "react";

const BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

interface CachedEntry {
  imageUrl: string;
  expiresAt: number;
}

interface BackendUnsplashResponse {
  images: string[];
}

const cache = new Map<string, CachedEntry[]>();

function isBackendResponse(data: unknown): data is BackendUnsplashResponse {
  return (
    typeof data === "object" &&
    data !== null &&
    "images" in data &&
    Array.isArray((data as Record<string, unknown>).images)
  );
}

/** Deterministic gradient from destination name — always looks polished */
function gradientFallback(destination: string, imageIndex: number): string {
  let hash = 0;
  for (let i = 0; i < destination.length; i++) {
    hash = ((hash << 5) - hash + destination.charCodeAt(i)) | 0;
  }
  // Mix in imageIndex so cards with the same destination get different gradients
  hash = ((hash << 5) - hash + imageIndex) | 0;
  const hue = Math.abs(hash) % 360;
  // Rich, travel-themed gradients (deep blues, warm ambers, forest greens, purples)
  const palettes = [
    "linear-gradient(135deg, #1a2a4a 0%, #2d4a7a 50%, #1e3a5f 100%)",
    "linear-gradient(135deg, #2c1810 0%, #8b4513 50%, #cd853f 100%)",
    "linear-gradient(135deg, #0d2137 0%, #1a4a6b 50%, #2980b9 100%)",
    "linear-gradient(135deg, #1a3a2a 0%, #2d6a4f 50%, #52b788 100%)",
    "linear-gradient(135deg, #2d1b4e 0%, #5a2d8a 50%, #8e44ad 100%)",
    "linear-gradient(135deg, #3d1c02 0%, #7b3f00 50%, #c17d3c 100%)",
    "linear-gradient(135deg, #0a2342 0%, #1c4f82 50%, #2874a6 100%)",
    "linear-gradient(135deg, #1b2838 0%, #2e4057 50%, #3d6b8a 100%)",
  ];
  // Use hue to pick from palette
  const idx = Math.floor((hue / 360) * palettes.length);
  return palettes[idx % palettes.length];
}

export interface DestinationImageResult {
  imageUrl: string | null;
  gradient: string;
  isLoading: boolean;
}

async function fetchUnsplashPhotos(
  destination: string,
  count: number
): Promise<CachedEntry[] | null> {
  const cacheKey = destination.toLowerCase().trim();
  const cached = cache.get(cacheKey);
  const now = Date.now();

  // Use cache if valid and has enough entries
  if (cached && cached.length >= count && cached[0].expiresAt > now) {
    return cached;
  }

  try {
    const enc = encodeURIComponent(destination);
    const url = `${BASE_URL}/unsplash/photo?destination=${enc}&count=${String(count)}`;
    const res = await fetch(url);
    if (!res.ok) return null;

    const raw: unknown = await res.json();
    if (!isBackendResponse(raw)) return null;
    if (raw.images.length === 0) return null;

    const expiresAt = now + CACHE_TTL_MS;
    const entries: CachedEntry[] = raw.images.map((imageUrl: string) => ({
      imageUrl,
      expiresAt,
    }));

    cache.set(cacheKey, entries);
    return entries;
  } catch {
    return null;
  }
}

export function useDestinationImage(
  destination: string,
  imageIndex = 0,
  totalCount = 1
): DestinationImageResult {
  const [entries, setEntries] = useState<CachedEntry[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (destination.length === 0) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    // Check cache synchronously first
    const cacheKey = destination.toLowerCase().trim();
    const cached = cache.get(cacheKey);
    const now = Date.now();
    if (cached && cached.length >= totalCount && cached[0].expiresAt > now) {
      setEntries(cached);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    void fetchUnsplashPhotos(destination, totalCount).then((r) => {
      if (!cancelled) {
        setEntries(r);
        setIsLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [destination, totalCount]);

  const entry =
    entries && entries.length > 0 ? entries[imageIndex % entries.length] : null;

  return {
    imageUrl: entry?.imageUrl ?? null,
    gradient: gradientFallback(destination, imageIndex),
    isLoading,
  };
}
