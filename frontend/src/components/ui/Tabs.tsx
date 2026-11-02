import type { ComponentProps } from "react";
import { Tabs as BaseTabs } from "@base-ui/react/tabs";
import { cn } from "@/lib/trip";

/** Controlled: <Tabs value onValueChange> — onValueChange receives the tab `value`. */
export const Tabs = BaseTabs.Root;

export function TabsList({ className, children, ...props }: ComponentProps<typeof BaseTabs.List>) {
  return (
    <BaseTabs.List
      className={cn(
        "relative flex [scrollbar-width:none] gap-1 overflow-x-auto shadow-[inset_0_-1px_0_var(--color-border)]",
        className
      )}
      {...props}
    >
      {children}
      <BaseTabs.Indicator className="absolute bottom-0 left-(--active-tab-left) h-0.5 w-(--active-tab-width) bg-accent-ink transition-[left,width] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]" />
    </BaseTabs.List>
  );
}

export function TabsTab({ className, ...props }: ComponentProps<typeof BaseTabs.Tab>) {
  return (
    <BaseTabs.Tab
      className={cn(
        "inline-flex h-11 shrink-0 items-center gap-1.5 px-2 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors hover:text-foreground data-active:text-foreground sm:px-3",
        className
      )}
      {...props}
    />
  );
}

export function TabsPanel({ className, ...props }: ComponentProps<typeof BaseTabs.Panel>) {
  return <BaseTabs.Panel className={cn("pt-5", className)} {...props} />;
}
