import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-4 py-4">
        <nav className="mx-auto flex max-w-7xl items-center justify-between">
          <Link to="/" className="text-xl font-bold text-brand">
            PackVote
          </Link>
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <span className="hidden text-sm text-black/60 sm:block">
                  {user?.email}
                </span>
                <Link
                  to="/dashboard"
                  className="text-sm text-black/70 hover:text-black"
                >
                  Dashboard
                </Link>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  className="text-black/70 hover:text-black hover:bg-transparent"
                >
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Link
                  to="/join"
                  className="text-sm text-black/70 hover:text-black"
                >
                  Join a Trip
                </Link>
                <Link
                  to="/login"
                  className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-hover"
                >
                  Sign In
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
