import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/trip";
import { Spinner } from "./Spinner";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "icon";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner and disables the button (keeps its width). */
  loading?: boolean;
}

const variants: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-foreground hover:brightness-95",
  secondary: "border border-muted-foreground bg-surface text-foreground hover:bg-muted",
  ghost: "text-foreground hover:bg-muted",
  danger: "bg-danger text-surface hover:opacity-90",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-sm pointer-coarse:h-11",
  md: "h-11 px-4 text-sm", // 44px touch target
  icon: "size-11",
};

/** Class string for link-as-button (`<Link className={buttonClass()}>`). */
export function buttonClass(variant: ButtonVariant = "primary", size: ButtonSize = "md"): string {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-lg font-medium whitespace-nowrap transition-[transform,opacity,background-color,filter] duration-150 select-none active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
    variants[variant],
    sizes[size]
  );
}

/** `type` defaults to "button"; pass type="submit" explicitly for form submit buttons. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading = false, className, disabled, children, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type="button"
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(buttonClass(variant, size), className)}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
});
