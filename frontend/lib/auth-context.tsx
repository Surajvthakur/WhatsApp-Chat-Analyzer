"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";

interface AuthUser {
  id: string;
  email: string;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = "auth_token";

function parseJwt(token: string): Record<string, unknown> | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join(""),
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function isTokenExpired(payload: Record<string, unknown>): boolean {
  const exp = payload.exp as number | undefined;
  if (!exp) return true;
  return Date.now() >= exp * 1000;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) {
      const payload = parseJwt(stored);
      if (payload && !isTokenExpired(payload)) {
        setToken(stored);
        setUser({ id: payload.sub as string, email: payload.email as string });
        
        // Ensure cookie is in sync
        const exp = payload.exp as number | undefined;
        const maxAge = exp ? Math.floor(exp - Date.now() / 1000) : 2592000;
        document.cookie = `${TOKEN_KEY}=${stored}; path=/; max-age=${maxAge}; SameSite=Lax`;
      } else {
        localStorage.removeItem(TOKEN_KEY);
        document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`;
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback((newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    const payload = parseJwt(newToken);
    if (payload) {
      const exp = payload.exp as number | undefined;
      const maxAge = exp ? Math.floor(exp - Date.now() / 1000) : 2592000;
      document.cookie = `${TOKEN_KEY}=${newToken}; path=/; max-age=${maxAge}; SameSite=Lax`;

      setToken(newToken);
      setUser({ id: payload.sub as string, email: payload.email as string });
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`;
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
