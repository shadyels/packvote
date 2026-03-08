import { useState, useEffect } from "react";
import { auth } from "@/lib/api";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export function useAuth(): AuthState & {
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
} {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setState({ user: null, isLoading: false, isAuthenticated: false });
      return;
    }

    auth
      .me()
      .then((user) => {
        setState({ user, isLoading: false, isAuthenticated: true });
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        setState({ user: null, isLoading: false, isAuthenticated: false });
      });
  }, []);

  const login = async (email: string, password: string) => {
    const { access_token } = await auth.login(email, password);
    localStorage.setItem("access_token", access_token);
    const user = await auth.me();
    setState({ user, isLoading: false, isAuthenticated: true });
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setState({ user: null, isLoading: false, isAuthenticated: false });
  };

  return { ...state, login, logout };
}
