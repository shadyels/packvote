import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <Link to="/" className="text-sm font-semibold text-brand">
            PackVote
          </Link>
          <p className="text-xs text-black/40">
            © {new Date().getFullYear()} PackVote. AI-powered group travel planning.
          </p>
        </div>
      </div>
    </footer>
  );
}
