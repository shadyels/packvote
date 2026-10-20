import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { auth, participants, ApiError, onUnauthorized } from "../api";

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

  describe("malformed error bodies", () => {
    it.each([null, { detail: [null, { msg: "bad" }] }])(
      "still throws ApiError (and signals 401) for body %j",
      async (body) => {
        const listener = vi.fn();
        const off = onUnauthorized(listener);
        localStorage.setItem("access_token", "stale");
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 401,
          statusText: "Unauthorized",
          json: () => Promise.resolve(body),
        });
        await expect(auth.me()).rejects.toBeInstanceOf(ApiError);
        expect(listener).toHaveBeenCalledTimes(1);
        off();
      }
    );
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

  describe("error messages", () => {
    it("joins Pydantic 422 detail arrays into a readable message", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        statusText: "Unprocessable Entity",
        json: () => Promise.resolve({ detail: [{ msg: "String too short" }, { msg: "Bad pin" }] }),
      });
      await expect(participants.accessByCode("A", "1")).rejects.toMatchObject({
        message: "String too short; Bad pin",
      });
    });

    it("falls back to the status text when the body has no detail", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Server Error",
        json: () => Promise.reject(new Error("not json")),
      });
      await expect(auth.me()).rejects.toMatchObject({ message: "Server Error" });
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

    it("does not fire when the session changed while the call was in flight", async () => {
      localStorage.setItem("access_token", "old");
      mockFetch.mockImplementationOnce(() => {
        localStorage.setItem("access_token", "new");
        return Promise.resolve(errorResponse(401, "Could not validate credentials"));
      });
      await expect(auth.me()).rejects.toBeInstanceOf(ApiError);
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
