import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/trip";

export const controlClass =
  "w-full rounded-lg border bg-surface px-3 text-base sm:text-sm text-foreground placeholder:text-muted-foreground transition-colors hover:border-muted-foreground/50 focus-visible:border-accent focus-visible:outline-1 focus-visible:outline-offset-0 aria-invalid:border-danger aria-invalid:focus-visible:outline-danger disabled:opacity-50";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(controlClass, "h-11", className)} {...props} />;
  }
);
