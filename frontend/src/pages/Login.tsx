import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/useAuth";
import { ApiError, auth } from "@/lib/api";
import { NAME_MAX, PASSWORD_MAX, PASSWORD_MIN } from "@/lib/trip";

const GENERIC_ERROR = "Something went wrong. Please try again.";

function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await auth.requestPasswordReset(email.trim());
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : GENERIC_ERROR);
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return (
      <p role="status" className="text-sm">
        If that email is registered, a reset link has been sent. Check your inbox.
      </p>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        void handleSubmit(e);
      }}
      className="flex flex-col gap-4"
    >
      <Field label="Email" required>
        {(c) => (
          <Input
            {...c}
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
            }}
            required
          />
        )}
      </Field>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <Button type="submit" loading={submitting}>
        Send reset link
      </Button>
    </form>
  );
}

export default function Login() {
  const { isAuthenticated, login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  const isLogin = mode === "login";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (isLogin) await login(email.trim(), password);
      else await register(email.trim(), password, name.trim() || undefined);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : GENERIC_ERROR);
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-sm py-8">
      <h1 className="text-2xl font-semibold tracking-tight">
        {isLogin ? "Sign in" : "Create your account"}
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {isLogin
          ? "Welcome back. Pick up where your group left off."
          : "Plan trips with your group."}
      </p>

      <form
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="mt-6 flex flex-col gap-4"
      >
        {!isLogin && (
          <Field label="Name">
            {(c) => (
              <Input
                {...c}
                autoComplete="name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                }}
                maxLength={NAME_MAX}
              />
            )}
          </Field>
        )}
        <Field label="Email" required>
          {(c) => (
            <Input
              {...c}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
              }}
              required
            />
          )}
        </Field>
        <Field label="Password" required>
          {(c) => (
            <Input
              {...c}
              type="password"
              autoComplete={isLogin ? "current-password" : "new-password"}
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
        {error && (
          <p role="alert" className="rounded-lg bg-danger-subtle px-3 py-2 text-sm text-danger">
            {error}
          </p>
        )}
        <Button type="submit" loading={submitting}>
          {submitting
            ? isLogin
              ? "Signing in…"
              : "Creating account…"
            : isLogin
              ? "Sign in"
              : "Create account"}
        </Button>
      </form>

      <div className="mt-4 flex items-center justify-between text-sm">
        <button
          type="button"
          className="inline-flex h-11 items-center text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          onClick={() => {
            setMode(isLogin ? "register" : "login");
            setError(null);
          }}
        >
          {isLogin ? "Need an account? Sign up" : "Have an account? Sign in"}
        </button>
        {isLogin && (
          <button
            type="button"
            className="inline-flex h-11 items-center text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            onClick={() => {
              setForgotOpen(true);
            }}
          >
            Forgot password?
          </button>
        )}
      </div>

      <Dialog open={forgotOpen} onOpenChange={setForgotOpen} title="Reset your password">
        <ForgotPasswordForm />
      </Dialog>
    </div>
  );
}
