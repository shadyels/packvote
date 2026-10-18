import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { ApiError, participants } from "@/lib/api";
import {
  ACTIVITY_TAG_MAX,
  ACTIVITY_TAGS_MAX_ITEMS,
  INTERESTS_MAX,
  NAME_MAX,
  formatShortDate,
  todayISO,
} from "@/lib/trip";

const CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SGD"];

interface PreferenceFormProps {
  token: string;
  proposedStart: string | null;
  proposedEnd: string | null;
  onSubmitted: () => void;
}

const num = (s: string) => (s.trim() === "" ? undefined : parseFloat(s));

export function PreferenceForm({
  token,
  proposedStart,
  proposedEnd,
  onSubmitted,
}: PreferenceFormProps) {
  const [name, setName] = useState("");
  const [start, setStart] = useState(proposedStart ?? "");
  const [end, setEnd] = useState(proposedEnd ?? "");
  const [budgetMin, setBudgetMin] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [interests, setInterests] = useState("");
  const [tags, setTags] = useState("");
  const [errors, setErrors] = useState<{ dates?: string; tags?: string; form?: string }>({});
  const [submitting, setSubmitting] = useState(false);

  const today = todayISO();
  const hint =
    proposedStart && proposedEnd
      ? `Organizer suggested ${formatShortDate(proposedStart)} – ${formatShortDate(proposedEnd)}. Change if needed.`
      : undefined;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const tagList = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const long = tagList.find((t) => t.length > ACTIVITY_TAG_MAX);
    const next: typeof errors = {};
    if ((start && start < today) || (end && end < today))
      next.dates = "Dates can't be in the past.";
    else if (start && end && end < start)
      next.dates = "End date must be on or after the start date.";
    if (tagList.length > ACTIVITY_TAGS_MAX_ITEMS)
      next.tags = `Too many activity tags — max ${ACTIVITY_TAGS_MAX_ITEMS.toString()}.`;
    else if (long)
      next.tags = `Tag "${long.slice(0, 20)}…" is too long — max ${ACTIVITY_TAG_MAX.toString()} characters.`;
    setErrors(next);
    if (next.dates || next.tags) return;

    setSubmitting(true);
    try {
      await participants.submitPreferences(token, {
        name: name.trim() || undefined,
        preferred_start_date: start || undefined,
        preferred_end_date: end || undefined,
        budget_min: num(budgetMin),
        budget_max: num(budgetMax),
        currency,
        interests: interests.trim() || undefined,
        activity_tags: tagList.length ? tagList : undefined,
      });
      toast.success("Preferences submitted");
      onSubmitted();
    } catch (err) {
      setErrors({
        form:
          err instanceof ApiError ? err.message : "Could not submit preferences. Please try again.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={(e) => {
        void handleSubmit(e);
      }}
      className="flex flex-col gap-4"
      noValidate
    >
      <Field label="Your name (optional)">
        {(c) => (
          <Input
            {...c}
            value={name}
            maxLength={NAME_MAX}
            onChange={(e) => {
              setName(e.target.value);
            }}
          />
        )}
      </Field>

      <fieldset className="flex flex-col gap-1.5">
        <legend className="sr-only">Travel dates</legend>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Earliest start" error={errors.dates}>
            {(c) => (
              <Input
                {...c}
                type="date"
                min={today}
                value={start}
                onChange={(e) => {
                  setStart(e.target.value);
                }}
              />
            )}
          </Field>
          <Field label="Latest end">
            {(c) => (
              <Input
                {...c}
                type="date"
                min={start || today}
                value={end}
                onChange={(e) => {
                  setEnd(e.target.value);
                }}
              />
            )}
          </Field>
        </div>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </fieldset>

      <div className="grid grid-cols-3 gap-3">
        <Field label="Budget min">
          {(c) => (
            <Input
              {...c}
              type="number"
              inputMode="decimal"
              min={0}
              className="tabular-nums"
              value={budgetMin}
              onChange={(e) => {
                setBudgetMin(e.target.value);
              }}
            />
          )}
        </Field>
        <Field label="Budget max">
          {(c) => (
            <Input
              {...c}
              type="number"
              inputMode="decimal"
              min={0}
              className="tabular-nums"
              value={budgetMax}
              onChange={(e) => {
                setBudgetMax(e.target.value);
              }}
            />
          )}
        </Field>
        <Field label="Currency">
          {(c) => (
            <Select
              {...c}
              value={currency}
              onChange={(e) => {
                setCurrency(e.target.value);
              }}
            >
              {CURRENCIES.map((cur) => (
                <option key={cur} value={cur}>
                  {cur}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>

      <Field label="Interests">
        {(c) => (
          <Textarea
            {...c}
            value={interests}
            maxLength={INTERESTS_MAX}
            placeholder="What do you love to do? (beaches, hiking, museums, food tours…)"
            onChange={(e) => {
              setInterests(e.target.value);
            }}
          />
        )}
      </Field>

      <Field
        label="Activity tags"
        hint="Comma-separated, e.g. hiking, street food"
        error={errors.tags}
      >
        {(c) => (
          <Input
            {...c}
            value={tags}
            maxLength={ACTIVITY_TAGS_MAX_ITEMS * (ACTIVITY_TAG_MAX + 2)}
            onChange={(e) => {
              setTags(e.target.value);
            }}
          />
        )}
      </Field>

      {errors.form && (
        <p role="alert" className="rounded-lg bg-danger-subtle px-3 py-2 text-sm text-danger">
          {errors.form}
        </p>
      )}
      <Button type="submit" loading={submitting}>
        Submit preferences
      </Button>
    </form>
  );
}
