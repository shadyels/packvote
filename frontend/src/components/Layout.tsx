import { Link } from "react-router-dom";

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-4 py-4">
        <nav className="mx-auto flex max-w-7xl items-center justify-between">
          <Link to="/" className="text-xl font-bold text-cream">
            PackVote
          </Link>
          <div className="flex gap-4">
            <Link to="/join" className="text-sm text-cream/70 hover:text-cream">
              Join a Trip
            </Link>
            <Link
              to="/login"
              className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-hover"
            >
              Sign In
            </Link>
          </div>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
