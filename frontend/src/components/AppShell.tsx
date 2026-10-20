import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { Toaster } from "@/components/ui/Toaster";

const navLink =
  "text-muted-foreground hover:text-foreground inline-flex h-11 items-center px-2 text-sm transition-colors";

export default function AppShell() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:ring-2 focus:ring-accent-ink"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
        <nav
          aria-label="Main"
          className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4"
        >
          <Link
            to="/"
            className="inline-flex h-11 items-center text-base font-semibold tracking-tight"
          >
            Pack<span className="text-accent-ink">Vote</span>
          </Link>
          <div className="flex items-center gap-1">
            {isAuthenticated ? (
              <>
                <span className="mr-2 hidden max-w-48 truncate text-sm text-muted-foreground sm:block">
                  {user?.email}
                </span>
                <Link to="/dashboard" className={navLink}>
                  Dashboard
                </Link>
                <Button variant="ghost" size="sm" onClick={handleLogout}>
                  Log out
                </Button>
              </>
            ) : (
              <>
                <Link to="/join" className={navLink}>
                  Join a trip
                </Link>
                {pathname !== "/login" && (
                  <Link to="/login" className={navLink}>
                    Sign in
                  </Link>
                )}
              </>
            )}
          </div>
        </nav>
      </header>
      <main
        id="main"
        tabIndex={-1}
        className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 outline-none"
      >
        <Outlet />
      </main>
      <footer className="border-t py-6 text-center text-xs text-muted-foreground">
        PackVote — group trips, decided fairly.
      </footer>
      <Toaster />
    </div>
  );
}
