import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button, buttonClass } from "@/components/ui/Button";
import { Toaster } from "@/components/ui/Toaster";

const navLink =
  "text-muted-foreground hover:text-foreground inline-flex h-11 items-center px-2 text-sm transition-colors";

export default function AppShell() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
        <nav
          aria-label="Main"
          className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4"
        >
          <Link to="/" className="text-base font-semibold tracking-tight">
            Pack<span className="text-accent">Vote</span>
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
                <Link to="/login" className={buttonClass("primary", "sm")}>
                  Sign in
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <footer className="border-t py-6 text-center text-xs text-muted-foreground">
        PackVote — group trips, decided together.
      </footer>
      <Toaster />
    </div>
  );
}
