import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { ApiError, auth } from "@/lib/api";
import { PASSWORD_MAX, PASSWORD_MIN } from "@/lib/trip";

const REDIRECT_MS = 2500;

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!done) return;
    const timer = setTimeout(() => {
      navigate("/login");
    }, REDIRECT_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [done, navigate]);

  if (!token) {
    return (
      <div className="mx-auto w-full max-w-sm py-8">
        <h1 className="text-2xl font-semibold tracking-tight">Reset password</h1>
        <p role="alert" className="mt-2 text-sm text-danger">
          This reset link is missing a token.
        </p>
        <Link to="/login" className="mt-4 inline-block text-sm underline underline-offset-4">
          Back to sign in
        </Link>
      </div>
    );
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setMismatch(true);
      return;
    }
    setMismatch(false);
    setSubmitting(true);
    try {
      await auth.confirmPasswordReset(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-sm py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Choose a new password</h1>
      {done ? (
        <div role="status" className="mt-4 text-sm">
          <p>Password updated. Redirecting to sign in…</p>
          <Link to="/login" className="mt-2 inline-block underline underline-offset-4">
            Sign in now
          </Link>
        </div>
      ) : (
        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="mt-6 flex flex-col gap-4"
        >
          <Field
            label="New password"
            hint={`Must be at least ${PASSWORD_MIN.toString()} characters.`}
            required
          >
            {(c) => (
              <Input
                {...c}
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                }}
                minLength={PASSWORD_MIN}
                maxLength={PASSWORD_MAX}
                required
              />
            )}
          </Field>
          <Field
            label="Confirm password"
            error={mismatch ? "Passwords do not match." : null}
            required
          >
            {(c) => (
              <Input
                {...c}
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => {
                  setConfirm(e.target.value);
                }}
                minLength={PASSWORD_MIN}
                maxLength={PASSWORD_MAX}
                required
              />
            )}
          </Field>
          {error && (
            <p role="alert" className="rounded-lg bg-danger-subtle px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}
          <Button type="submit" loading={submitting}>
            Update password
          </Button>
        </form>
      )}
    </div>
  );
}
