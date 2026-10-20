import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  text: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, text, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed px-6 py-12 text-center">
      <Icon className="size-6 text-muted-foreground" aria-hidden="true" />
      <h2 className="mt-3 text-sm font-semibold">{title}</h2>
      <p className="mt-1 max-w-xs text-sm text-muted-foreground">{text}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
