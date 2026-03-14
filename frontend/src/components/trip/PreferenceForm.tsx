import { useState } from "react";
import { participants as participantsApi, ApiError } from "@/lib/api";

const CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SGD"];

interface PreferenceFormProps {
  token: string;
  onSuccess: () => void;
}

export function PreferenceForm({ token, onSuccess }: PreferenceFormProps) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [budgetMin, setBudgetMin] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [interests, setInterests] = useState("");
  const [activityTags, setActivityTags] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const tags = activityTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      await participantsApi.submitPreferences(token, {
        preferred_start_date: startDate || undefined,
        preferred_end_date: endDate || undefined,
        budget_min: budgetMin ? parseFloat(budgetMin) : undefined,
        budget_max: budgetMax ? parseFloat(budgetMax) : undefined,
        currency,
        interests: interests || undefined,
        activity_tags: tags.length > 0 ? tags : undefined,
      });
      onSuccess();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to submit preferences."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-5">
      <div>
        <h2 className="text-base font-semibold text-foreground">
          Your Preferences
        </h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Share what you're looking for so we can find the best destination for
          your group.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="space-y-4"
      >
        {/* Dates */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-foreground mb-1">
              Preferred Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
              }}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-foreground mb-1">
              Preferred End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
              }}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
            />
          </div>
        </div>

        {/* Budget */}
        <div className="space-y-2">
          <label className="block text-xs font-medium text-foreground">
            Budget Range
          </label>
          <div className="grid grid-cols-3 gap-2">
            <input
              type="number"
              value={budgetMin}
              onChange={(e) => {
                setBudgetMin(e.target.value);
              }}
              placeholder="Min"
              min={0}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
            />
            <input
              type="number"
              value={budgetMax}
              onChange={(e) => {
                setBudgetMax(e.target.value);
              }}
              placeholder="Max"
              min={0}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
            />
            <select
              value={currency}
              onChange={(e) => {
                setCurrency(e.target.value);
              }}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Interests */}
        <div>
          <label className="block text-xs font-medium text-foreground mb-1">
            Interests
          </label>
          <textarea
            value={interests}
            onChange={(e) => {
              setInterests(e.target.value);
            }}
            placeholder="What do you love to do? (beaches, hiking, museums, food tours…)"
            rows={3}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50 resize-none"
          />
        </div>

        {/* Activity tags */}
        <div>
          <label className="block text-xs font-medium text-foreground mb-1">
            Activity Tags
            <span className="text-muted-foreground font-normal ml-1">
              (comma-separated)
            </span>
          </label>
          <input
            type="text"
            value={activityTags}
            onChange={(e) => {
              setActivityTags(e.target.value);
            }}
            placeholder="outdoor, nightlife, family-friendly, budget"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand/50"
          />
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? "Submitting…" : "Submit Preferences"}
        </button>
      </form>
    </div>
  );
}
