export function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="border-t-2 border-foreground pt-4">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-1 max-w-prose text-sm text-muted-foreground">{text}</p>
    </div>
  );
}
