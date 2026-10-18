import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { ApiError, participants } from "@/lib/api";

export default function Join() {
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await participants.accessByCode(code.toUpperCase().trim(), pin.trim());
      navigate(`/trip/${res.token}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 404
            ? "Invalid trip code or PIN. Please check and try again."
            : err.message
          : "Something went wrong. Please try again."
      );
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto w-full max-w-sm animate-slide-up px-4 py-12">
      <h1 className="text-2xl font-semibold tracking-tight">Join a trip</h1>
      <p className="mt-1 mb-6 text-sm text-muted-foreground">
        Enter the trip code and PIN from your invitation. Invited by email? Use the link in that
        email instead.
      </p>
      <form
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="flex flex-col gap-4"
      >
        <Field label="Trip code" required>
          {(c) => (
            <Input
              {...c}
              required
              maxLength={8}
              autoComplete="off"
              autoCapitalize="characters"
              className="font-mono tracking-widest uppercase"
              value={code}
              onChange={(e) => {
                setCode(e.target.value);
              }}
            />
          )}
        </Field>
        <Field label="PIN" required>
          {(c) => (
            <Input
              {...c}
              required
              inputMode="numeric"
              maxLength={4}
              autoComplete="off"
              className="font-mono tracking-widest"
              value={pin}
              onChange={(e) => {
                setPin(e.target.value.replace(/\D/g, ""));
              }}
            />
          )}
        </Field>
        {error && (
          <p role="alert" className="rounded-lg bg-danger-subtle px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}
        <Button type="submit" loading={submitting}>
          Join trip
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        Organizing a trip?{" "}
        <Link to="/login" className="font-medium text-foreground underline underline-offset-4">
          Sign in
        </Link>
      </p>
    </main>
  );
}
