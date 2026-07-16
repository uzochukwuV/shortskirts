import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, AuthResponse, clearAuthToken, setAuthToken, User, getAuthToken } from "@/lib/api";

type AuthContextValue = {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadUser() {
      if (!getAuthToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const me = await api.me();
        if (!cancelled) setUser(me);
      } catch {
        clearAuthToken();
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    loadUser();
    return () => { cancelled = true; };
  }, []);

  async function applyAuth(result: AuthResponse) {
    setAuthToken(result.token);
    setUser(result.user);
  }

  const value = useMemo<AuthContextValue>(() => ({
    user,
    isLoading,
    isAuthenticated: !!user,
    login: async (email, password) => applyAuth(await api.login({ email, password })),
    register: async (email, password) => applyAuth(await api.register({ email, password })),
    logout: async () => {
      try { await api.logout(); } catch {}
      clearAuthToken();
      setUser(null);
    },
  }), [user, isLoading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
