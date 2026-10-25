import { Navigate } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { useMe } from "@/lib/auth";
import { roleOf, type Role } from "@/lib/roles";

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const me = useMe();
  if (!roles.includes(roleOf(me))) return <Navigate to="/dashboard" />;
  return <>{children}</>;
}
