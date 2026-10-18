import { useState, type FormEvent } from "react";
import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { ApiError, trips } from "@/lib/api";
import {
  DESTINATION_MAX,
  NOTES_MAX,
  PARTICIPANT_EMAILS_MAX,
  TITLE_MAX,
  daysBetween,
  maxTripDays,
  todayISO,
} from "@/lib/trip";
import type { Trip } from "@/types";

interface TripFormProps {
  /** Present = edit mode (prefilled, no participant emails). Absent = create mode. */
  trip?: Trip;
  onDone: (trip: Trip) => void;
  onCancel?: () => void;
}

// Backend returns datetimes; the date inputs want yyyy-MM-dd.
const dateOnly = (v: string | null | undefined) => v?.slice(0, 10) ?? "";

export function TripForm({ trip, onDone, onCancel }: TripFormProps) {
  const isEdit = trip !== undefined;
  const [title, setTitle] = useState(trip?.title ?? "");
  const [destination, setDestination] = useState(trip?.destination ?? "");
  const [start, setStart] = useState(dateOnly(trip?.proposed_start_date));
  const [end, setEnd] = useState(dateOnly(trip?.proposed_end_date));
  const [numOptions, setNumOptions] = useState(trip?.num_options ?? 3);
  const [emails, setEmails] = useState<string[]>([""]);
  const [notes, setNotes] = useState(trip?.notes ?? "");
  const [errors, setErrors] = useState<{ dates?: string; emails?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const cap = maxTripDays(numOptions);
    const next: typeof errors = {};
    if (start && end && end < start) next.dates = "End date must be on or after the start date.";
    else if (start && end && daysBetween(start, end) > cap)
      next.dates = `Date range too long — max ${cap.toString()} days for ${numOptions.toString()} itinerary options.`;
    const cleanEmails = emails.map((v) => v.trim()).filter(Boolean);
    if (!isEdit && cleanEmails.length === 0) next.emails = "Add at least one participant email.";
    setErrors(next);
    if (next.dates || next.emails) return;

    // The backend ignores null/omitted fields on PATCH but stores "" — so send "" to clear.
    const common = {
      title: title.trim(),
      num_options: numOptions,
      proposed_start_date: start || undefined,
      proposed_end_date: end || undefined,
    };
    setSubmitting(true);
    try {
      const saved = trip
        ? await trips.update(trip.id, {
            ...common,
            destination: destination.trim(),
            notes: notes.trim(),
          })
        : await trips.create({
            ...common,
            destination: destination.trim() || undefined,
            notes: notes.trim() || undefined,
            participant_emails: cleanEmails,
          });
      onDone(saved);
    } catch (err) {
      setFormError(
        err instanceof ApiError
          ? err.message
          : `Could not ${isEdit ? "save" : "create"} the trip. Please try again.`
      );
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
    >
      <Field label="Title" required>
        {(c) => (
          <Input
            {...c}
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
            }}
            maxLength={TITLE_MAX}
            required
          />
        )}
      </Field>
      <Field label="Destination" hint="Leave blank to let the AI suggest destinations.">
        {(c) => (
          <Input
            {...c}
            value={destination}
            onChange={(e) => {
              setDestination(e.target.value);
            }}
            maxLength={DESTINATION_MAX}
          />
        )}
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Earliest start">
          {(c) => (
            <Input
              {...c}
              type="date"
              value={start}
              required={isEdit && !!dateOnly(trip.proposed_start_date)}
              min={isEdit ? undefined : todayISO()}
              onChange={(e) => {
                setStart(e.target.value);
              }}
            />
          )}
        </Field>
        <Field label="Latest end" error={errors.dates}>
          {(c) => (
            <Input
              {...c}
              type="date"
              value={end}
              required={isEdit && !!dateOnly(trip.proposed_end_date)}
              min={start || (isEdit ? undefined : todayISO())}
              onChange={(e) => {
                setEnd(e.target.value);
              }}
            />
          )}
        </Field>
      </div>
      <Field label="Itinerary options">
        {(c) => (
          <Select
            {...c}
            value={numOptions}
            onChange={(e) => {
              setNumOptions(Number(e.target.value));
            }}
          >
            {[2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </Select>
        )}
      </Field>

      {!isEdit && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1.5 text-sm font-medium">
            Participants{" "}
            <span className="text-danger" aria-hidden="true">
              *
            </span>
          </legend>
          {emails.map((value, i) => (
            <div key={i} className="flex gap-2">
              <Input
                type="email"
                aria-label={`Participant email ${(i + 1).toString()}`}
                placeholder="friend@example.com"
                value={value}
                onChange={(e) => {
                  setEmails(emails.map((v, j) => (j === i ? e.target.value : v)));
                }}
              />
              {emails.length > 1 && (
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove participant ${(i + 1).toString()}`}
                  onClick={() => {
                    setEmails(emails.filter((_, j) => j !== i));
                  }}
                >
                  <X className="size-4" aria-hidden="true" />
                </Button>
              )}
            </div>
          ))}
          {errors.emails && (
            <p role="alert" className="text-xs text-danger">
              {errors.emails}
            </p>
          )}
          {emails.length < PARTICIPANT_EMAILS_MAX && (
            <Button
              variant="ghost"
              size="sm"
              className="self-start"
              onClick={() => {
                setEmails([...emails, ""]);
              }}
            >
              <Plus className="size-4" aria-hidden="true" />
              Add participant
            </Button>
          )}
        </fieldset>
      )}

      <Field label="Notes">
        {(c) => (
          <Textarea
            {...c}
            value={notes}
            onChange={(e) => {
              setNotes(e.target.value);
            }}
            maxLength={NOTES_MAX}
          />
        )}
      </Field>

      {formError && (
        <p role="alert" className="rounded-lg bg-danger-subtle px-3 py-2 text-sm text-danger">
          {formError}
        </p>
      )}
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" loading={submitting}>
          {isEdit ? "Save changes" : "Create trip"}
        </Button>
      </div>
    </form>
  );
}
