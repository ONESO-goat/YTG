import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, setUnauthorizedHandler, tokenStore } from "./api";
import type { Me, UserType } from "./types";

type AuthStatus = "loading" | "anonymous" | "authenticated";

interface AuthContextValue {
  status: AuthStatus;
  me: Me | null;
  login: (identifier: string, password: string) => Promise<Me>;
  signup: (body: {
    username: string;
    email: string;
    password: string;
    user_type: UserType;
  }) => Promise<Me>;
  logout: () => void;
  refresh: () => Promise<unknown>;
  /** Swap in a new token for the same user, e.g. after a password change. */
  adoptToken: (token: string) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const meQueryKey = ["me"] as const;

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(() => tokenStore.get());

  const meQuery = useQuery({
    queryKey: meQueryKey,
    queryFn: api.me,
    enabled: !!token,
    staleTime: 30_000,
  });

  const logout = useCallback(() => {
    tokenStore.set(null);
    setToken(null);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, [logout]);

  const startSession = useCallback(
    async (accessToken: string) => {
      tokenStore.set(accessToken);
      queryClient.clear();
      setToken(accessToken);
      return queryClient.fetchQuery({ queryKey: meQueryKey, queryFn: api.me });
    },
    [queryClient],
  );

  const value = useMemo<AuthContextValue>(() => {
    let status: AuthStatus = "anonymous";
    if (token) status = meQuery.data ? "authenticated" : meQuery.isError ? "anonymous" : "loading";
    return {
      status,
      me: token ? (meQuery.data ?? null) : null,
      login: async (identifier, password) =>
        startSession((await api.login({ identifier, password })).access_token),
      signup: async (body) => startSession((await api.signup(body)).access_token),
      logout,
      refresh: () => queryClient.invalidateQueries({ queryKey: meQueryKey }),
      adoptToken: (accessToken) => {
        tokenStore.set(accessToken);
        setToken(accessToken);
      },
    };
  }, [token, meQuery.data, meQuery.isError, startSession, logout, queryClient]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

/** The signed-in user's data; only use below the authenticated layout. */
export function useMe(): Me {
  const { me } = useAuth();
  if (!me) throw new Error("useMe used outside an authenticated route");
  return me;
}

/** Where a signed-in user belongs, based on how far through setup they are. */
export function homePath(me: Me): "/dashboard" | "/onboarding" | "/waiting" {
  if (me.guardian) return "/dashboard";
  return me.user.user_type === "dependent" ? "/waiting" : "/onboarding";
}
