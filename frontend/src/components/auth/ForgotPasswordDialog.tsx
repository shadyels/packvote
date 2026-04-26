import { useState } from "react";
import { auth, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

interface ForgotPasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ForgotPasswordDialog({ open, onOpenChange }: ForgotPasswordDialogProps) {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      setEmail("");
      setError(null);
      setSubmitted(false);
    }
    onOpenChange(nextOpen);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await auth.requestPasswordReset(email);
      setSubmitted(true);
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
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent showCloseButton>
        <DialogHeader>
          <DialogTitle className="text-black">Reset your password</DialogTitle>
          <DialogDescription>
            {submitted
              ? "Check your inbox for next steps."
              : "Enter your email and we'll send a reset link if an account exists."}
          </DialogDescription>
        </DialogHeader>

        {submitted ? (
          <p className="text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
            If that email is registered, a reset link has been sent. Check your inbox.
          </p>
        ) : (
          <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="reset-email" className="text-black/80">
                Email
              </Label>
              <Input
                id="reset-email"
                type="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={(e) => { setEmail(e.target.value); }}
                className="bg-card border-border text-black placeholder:text-black/40"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                {error}
              </p>
            )}

            <DialogFooter className="border-t-0 bg-transparent p-0 -mx-0 -mb-0 rounded-none">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-brand hover:bg-brand-hover text-white font-semibold"
              >
                {isSubmitting ? "Sending…" : "Send reset link"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
