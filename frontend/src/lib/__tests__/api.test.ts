import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { auth, participants, votes, ApiError, onUnauthorized } from "../api";

// ---------------------------------------------------------------------------
// Mock fetch globally
// ---------------------------------------------------------------------------

const mockFetch = vi.fn();

function okResponse(data: unknown) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  };
}

function errorResponse(status: number, detail: string) {
  return {
    ok: false,
    status,
    statusText: "Error",
    json: () => Promise.resolve({ detail }),
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("API client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    vi.stubGlobal("fetch", mockFetch);
    window.localStorage.removeItem("access_token");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("auth header injection", () => {
    it("omits Authorization when no token in localStorage", async () => {
      mockFetch.mockResolvedValueOnce(
        okResponse({ id: 1, email: "a@a.com", full_name: null, created_at: "" })
      );
      await auth.me();
      const [, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = opts.headers as Record<string, string>;
      expect(headers["Authorization"]).toBeUndefined();
    });

    it("adds Bearer token when access_token is in localStorage", async () => {
      localStorage.setItem("access_token", "my-jwt");
      mockFetch.mockResolvedValueOnce(
        okResponse({ id: 1, email: "a@a.com", full_name: null, created_at: "" })
      );
      await auth.me();
      const [, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = opts.headers as Record<string, string>;
      expect(headers["Authorization"]).toBe("Bearer my-jwt");
    });
  });

  describe("error handling", () => {
    it("throws ApiError on non-ok response", async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(404, "Not found"));
      await expect(auth.me()).rejects.toBeInstanceOf(ApiError);
    });

    it("ApiError carries the HTTP status code", async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(401, "Unauthorized"));
      try {
        await auth.me();
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError);
        expect((e as ApiError).status).toBe(401);
      }
    });

    it("ApiError carries the detail message from the response body", async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(400, "Bad request detail"));
      try {
        await auth.me();
      } catch (e) {
        expect((e as ApiError).message).toBe("Bad request detail");
      }
    });
  });

  describe("auth.login", () => {
    it("sends correct JSON payload", async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ access_token: "tok", token_type: "bearer" }));
      await auth.login("user@example.com", "secret");
      const [, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(JSON.parse(opts.body as string)).toEqual({
        email: "user@example.com",
        password: "secret",
      });
    });
  });

  describe("auth.register", () => {
    it("sends email, password, and full_name", async () => {
      mockFetch.mockResolvedValueOnce(
        okResponse({ id: 1, email: "a@a.com", full_name: "Alice", created_at: "" })
      );
      await auth.register("a@a.com", "pass", "Alice");
      const [, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(JSON.parse(opts.body as string)).toEqual({
        email: "a@a.com",
        password: "pass",
        full_name: "Alice",
      });
    });
  });

  describe("participants.accessByCode", () => {
    it("sends trip_code and pin in the body", async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ token: "part-tok", participant: {} }));
      await participants.accessByCode("ABCD1234", "5678");
      const [, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(JSON.parse(opts.body as string)).toEqual({
        trip_code: "ABCD1234",
        pin: "5678",
      });
    });
  });

  describe("votes.getResults", () => {
    it("omits query string when iteration is not provided", async () => {
      mockFetch.mockResolvedValueOnce(okResponse({}));
      await votes.getResults(42);
      const [url] = mockFetch.mock.calls[0] as [string];
      expect(url).not.toContain("iteration");
    });

    it("appends ?iteration=N when iteration is provided", async () => {
      mockFetch.mockResolvedValueOnce(okResponse({}));
      await votes.getResults(42, 3);
      const [url] = mockFetch.mock.calls[0] as [string];
      expect(url).toContain("?iteration=3");
    });
  });
  describe("votes.getResults participant token", () => {
    it("sends X-Participant-Token when provided", async () => {
      mockFetch.mockResolvedValueOnce(okResponse({}));
      await votes.getResults(42, undefined, "part-tok");
      const [, opts] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = opts.headers as Record<string, string>;
      expect(headers["X-Participant-Token"]).toBe("part-tok");
    });
  });

  describe("204 responses", () => {
    it("resolves to null", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });
      const { trips } = await import("../api");
      await expect(trips.delete(1)).resolves.toBeNull();
    });
  });

  describe("401 logout signal", () => {
    const listener = vi.fn();
    let off: () => void;

    beforeEach(() => {
      listener.mockReset();
      off = onUnauthorized(listener);
    });
    afterEach(() => {
      off();
    });

    it("fires for a 401 on a JWT-authenticated call", async () => {
      localStorage.setItem("access_token", "stale");
      mockFetch.mockResolvedValueOnce(errorResponse(401, "Could not validate credentials"));
      await expect(auth.me()).rejects.toBeInstanceOf(ApiError);
      expect(listener).toHaveBeenCalledTimes(1);
    });

    it("does not fire for a failed login", async () => {
      localStorage.setItem("access_token", "stale");
      mockFetch.mockResolvedValueOnce(errorResponse(401, "Invalid credentials"));
      await expect(auth.login("a@a.com", "bad")).rejects.toBeInstanceOf(ApiError);
      expect(listener).not.toHaveBeenCalled();
    });

    it("does not fire for a participant-token call", async () => {
      localStorage.setItem("access_token", "stale");
      mockFetch.mockResolvedValueOnce(errorResponse(401, "Could not validate credentials"));
      await expect(votes.getResults(1, undefined, "part-tok")).rejects.toBeInstanceOf(ApiError);
      expect(listener).not.toHaveBeenCalled();
    });

    it("does not fire when no JWT is stored", async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(401, "Not authenticated"));
      await expect(auth.me()).rejects.toBeInstanceOf(ApiError);
      expect(listener).not.toHaveBeenCalled();
    });

    it("does not fire for non-401 errors", async () => {
      localStorage.setItem("access_token", "tok");
      mockFetch.mockResolvedValueOnce(errorResponse(403, "Forbidden"));
      await expect(auth.me()).rejects.toBeInstanceOf(ApiError);
      expect(listener).not.toHaveBeenCalled();
    });
  });
});
