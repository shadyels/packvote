import type { CSSProperties } from "react";
import { Toaster as Sonner } from "sonner";

/** Mount once (AppShell). Use `toast.success(...)` / `toast.error(...)` from "sonner". */
export function Toaster() {
  return (
    <Sonner
      theme="system"
      position="bottom-center"
      style={
        {
          "--normal-bg": "var(--color-surface)",
          "--normal-text": "var(--color-foreground)",
          "--normal-border": "var(--color-border)",
        } as CSSProperties
      }
    />
  );
}
