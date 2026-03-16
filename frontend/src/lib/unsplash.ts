import { useState, useEffect } from "react";

const UNSPLASH_BASE = "https://api.unsplash.com";
const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

interface CachedResult {
  imageUrl: string;
  photographer: string | null;
  photographerUrl: string | null;
  expiresAt: number;
}

interface UnsplashPhoto {
  urls: { regular: string };
  user: { name: string; links: { html: string } };
}

interface UnsplashSearchResponse {
  results: UnsplashPhoto[];
}

const cache = new Map<string, CachedResult>();

function isSearchResponse(data: unknown): data is UnsplashSearchResponse {
  return (
    typeof data === "object" &&
    data !== null &&
    "results" in data &&
    Array.isArray((data as Record<string, unknown>).results)
  );
}

/** Deterministic gradient from destination name — always looks polished */
function gradientFallback(destination: string): string {
  let hash = 0;
  for (let i = 0; i < destination.length; i++) {
    hash = ((hash << 5) - hash + destination.charCodeAt(i)) | 0;
  }
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
  photographer: string | null;
  photographerUrl: string | null;
  isLoading: boolean;
}

async function fetchUnsplashPhoto(destination: string): Promise<CachedResult | null> {
  const apiKey = import.meta.env.VITE_UNSPLASH_ACCESS_KEY as string | undefined;
  if (!apiKey) return null;

  const cacheKey = destination.toLowerCase().trim();
  const cached = cache.get(cacheKey);
  if (cached && cached.expiresAt > Date.now()) {
    return cached;
  }

  try {
    const query = encodeURIComponent(`${destination} travel landscape`);
    const url = `${UNSPLASH_BASE}/search/photos?query=${query}&orientation=landscape&per_page=1`;
    const res = await fetch(url, {
      headers: { Authorization: `Client-ID ${apiKey}` },
    });
    if (!res.ok) return null;

    const raw: unknown = await res.json();
    if (!isSearchResponse(raw)) return null;
    const photo: UnsplashPhoto | undefined =
      raw.results.length > 0 ? raw.results[0] : undefined;
    if (!photo) return null;

    const result: CachedResult = {
      imageUrl: photo.urls.regular,
      photographer: photo.user.name,
      photographerUrl: photo.user.links.html,
      expiresAt: Date.now() + CACHE_TTL_MS,
    };
    cache.set(cacheKey, result);
    return result;
  } catch {
    return null;
  }
}

export function useDestinationImage(destination: string): DestinationImageResult {
  const [result, setResult] = useState<CachedResult | null>(null);
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
    if (cached && cached.expiresAt > Date.now()) {
      setResult(cached);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    void fetchUnsplashPhoto(destination).then((r) => {
      if (!cancelled) {
        setResult(r);
        setIsLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [destination]);

  return {
    imageUrl: result?.imageUrl ?? null,
    gradient: gradientFallback(destination),
    photographer: result?.photographer ?? null,
    photographerUrl: result?.photographerUrl ?? null,
    isLoading,
  };
}
