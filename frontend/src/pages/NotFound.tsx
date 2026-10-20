import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="animate-fade-in py-16 text-center">
      <p className="font-mono text-sm text-muted-foreground">404</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        That page doesn&apos;t exist or the link has changed.
      </p>
      <Link
        to="/"
        className="mt-6 inline-block text-sm font-medium text-accent-ink hover:underline"
      >
        Back to home
      </Link>
    </div>
  );
}
