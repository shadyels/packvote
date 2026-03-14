import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError } from "@/lib/api";

type Mode = "login" | "register";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, register } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName || undefined);
      }
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link to="/" className="text-2xl font-bold text-accent">
            PackVote
          </Link>
        </div>

        <Card className="bg-white border-border">
          <CardHeader>
            <CardTitle className="text-black">
              {mode === "login" ? "Welcome back" : "Create an account"}
            </CardTitle>
            <CardDescription className="text-black/60">
              {mode === "login"
                ? "Sign in to manage your trips"
                : "Start planning group trips"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-4">
              {mode === "register" && (
                <div className="space-y-1.5">
                  <Label htmlFor="fullName" className="text-black/80">
                    Name (optional)
                  </Label>
                  <Input
                    id="fullName"
                    type="text"
                    placeholder="Your name"
                    value={fullName}
                    onChange={(e) => { setFullName(e.target.value); }}
                    className="bg-white border-border text-black placeholder:text-black/40"
                  />
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-black/80">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  required
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); }}
                  className="bg-white border-border text-black placeholder:text-black/40"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-black/80">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); }}
                  className="bg-white border-border text-black placeholder:text-black/40"
                />
              </div>

              {error && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-accent hover:bg-accent-hover text-white font-semibold"
              >
                {isSubmitting
                  ? mode === "login"
                    ? "Signing in…"
                    : "Creating account…"
                  : mode === "login"
                    ? "Sign in"
                    : "Create account"}
              </Button>
            </form>

            <div className="mt-4 text-center text-sm text-black/60">
              {mode === "login" ? (
                <>
                  Don&apos;t have an account?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMode("register");
                      setError(null);
                    }}
                    className="text-accent hover:underline"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setMode("login");
                      setError(null);
                    }}
                    className="text-accent hover:underline"
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
