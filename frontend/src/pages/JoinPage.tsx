import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { participants as participantsApi, ApiError } from "@/lib/api";

export default function JoinPage() {
  const navigate = useNavigate();
  const [tripCode, setTripCode] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const result = await participantsApi.accessByCode(
        tripCode.toUpperCase().trim(),
        pin.trim()
      );
      navigate(`/trip/${result.token}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 404
            ? "Invalid trip code or PIN. Please check and try again."
            : err.message
        );
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm rounded-lg border border-border bg-card p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-foreground">Join a Trip</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Enter your Trip Code and PIN to access your trip.
        </p>

        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="mt-6 space-y-4"
        >
          <div>
            <label
              htmlFor="trip-code"
              className="block text-sm font-medium text-foreground mb-1"
            >
              Trip Code
            </label>
            <input
              id="trip-code"
              type="text"
              value={tripCode}
              onChange={(e) => {
                setTripCode(e.target.value);
              }}
              placeholder="e.g. ABCD1234"
              maxLength={8}
              required
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono uppercase text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
            />
          </div>

          <div>
            <label
              htmlFor="pin"
              className="block text-sm font-medium text-foreground mb-1"
            >
              PIN
            </label>
            <input
              id="pin"
              type="text"
              inputMode="numeric"
              value={pin}
              onChange={(e) => {
                setPin(e.target.value.replace(/\D/g, "").slice(0, 4));
              }}
              placeholder="4 digits"
              maxLength={4}
              required
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "Joining…" : "Join Trip"}
          </button>
        </form>
      </div>
    </main>
  );
}
