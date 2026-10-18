import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/trip";
import { controlClass } from "./Input";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, rows = 3, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={cn(controlClass, "min-h-20 py-2.5", className)}
      {...props}
    />
  );
});
