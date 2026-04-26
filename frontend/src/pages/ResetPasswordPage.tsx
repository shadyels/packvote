import { useState } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import { auth, ApiError } from "@/lib/api";
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

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!token) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <Link to="/" className="text-2xl font-bold text-brand">
              PackVote
            </Link>
          </div>
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-black">Invalid link</CardTitle>
              <CardDescription className="text-black/60">
                This reset link is missing a token.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link to="/login" className="text-sm text-brand hover:underline">
                Back to sign in
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await auth.confirmPasswordReset(token, newPassword);
      setSuccess(true);
      setTimeout(() => { navigate("/login"); }, 2500);
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
          <Link to="/" className="text-2xl font-bold text-brand">
            PackVote
          </Link>
        </div>

        <Card className="bg-card border-border">
          <CardHeader>
            <CardTitle className="text-black">Choose a new password</CardTitle>
            <CardDescription className="text-black/60">
              Must be at least 8 characters.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {success ? (
              <div className="space-y-4">
                <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
                  Password updated. Redirecting to sign in…
                </p>
                <Link
                  to="/login"
                  className="block text-center text-sm text-brand hover:underline"
                >
                  Sign in now
                </Link>
              </div>
            ) : (
              <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="new-password" className="text-black/80">
                    New password
                  </Label>
                  <Input
                    id="new-password"
                    type="password"
                    placeholder="••••••••"
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => { setNewPassword(e.target.value); }}
                    className="bg-card border-border text-black placeholder:text-black/40"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="confirm-password" className="text-black/80">
                    Confirm password
                  </Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    placeholder="••••••••"
                    required
                    minLength={8}
                    value={confirmPassword}
                    onChange={(e) => { setConfirmPassword(e.target.value); }}
                    className="bg-card border-border text-black placeholder:text-black/40"
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
                  className="w-full bg-brand hover:bg-brand-hover text-white font-semibold"
                >
                  {isSubmitting ? "Updating…" : "Update password"}
                </Button>

                <div className="text-center text-sm text-black/60">
                  <Link to="/login" className="text-brand hover:underline">
                    Back to sign in
                  </Link>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
