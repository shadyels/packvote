import type { ComponentProps } from "react";
import { Tabs as BaseTabs } from "@base-ui/react/tabs";
import { cn } from "@/lib/trip";

/** Controlled: <Tabs value onValueChange> — onValueChange receives the tab `value`. */
export const Tabs = BaseTabs.Root;

export function TabsList({ className, ...props }: ComponentProps<typeof BaseTabs.List>) {
  return (
    <BaseTabs.List
      className={cn("flex [scrollbar-width:none] gap-1 overflow-x-auto border-b", className)}
      {...props}
    />
  );
}

export function TabsTab({ className, ...props }: ComponentProps<typeof BaseTabs.Tab>) {
  return (
    <BaseTabs.Tab
      className={cn(
        "-mb-px inline-flex h-11 shrink-0 items-center gap-1.5 border-b-2 border-transparent px-2 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors hover:text-foreground data-active:border-accent-ink data-active:text-foreground sm:px-3",
        className
      )}
      {...props}
    />
  );
}

export function TabsPanel({ className, ...props }: ComponentProps<typeof BaseTabs.Panel>) {
  return <BaseTabs.Panel className={cn("pt-5", className)} {...props} />;
}
