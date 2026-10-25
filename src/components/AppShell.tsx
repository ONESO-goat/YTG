import { Link } from "@tanstack/react-router";
import {
  Bell,
  Gem,
  LayoutDashboard,
  LogOut,
  PlayCircle,
  Settings,
  ShoppingBag,
  UserCircle,
} from "lucide-react";
import type { ReactNode } from "react";
import { formatPoints, Logo } from "@/components/common";
import { useAuth, useMe } from "@/lib/auth";
import { roleOf, type Role } from "@/lib/roles";

const NAV: { to: string; label: string; icon: typeof Bell; roles: Role[] }[] = [
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    roles: ["personal", "family-owner", "member"],
  },
  { to: "/monitor", label: "Session", icon: PlayCircle, roles: ["personal", "member"] },
  { to: "/shop", label: "Shop", icon: ShoppingBag, roles: ["personal", "member"] },
  { to: "/reports", label: "Reports", icon: Bell, roles: ["personal", "family-owner"] },
  { to: "/settings", label: "Settings", icon: Settings, roles: ["personal", "family-owner"] },
  {
    to: "/account",
    label: "Account",
    icon: UserCircle,
    roles: ["personal", "family-owner", "member"],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  const me = useMe();
  const { logout } = useAuth();
  const role = roleOf(me);
  const links = NAV.filter((l) => l.roles.includes(role));
  const showPoints = role !== "family-owner";

  return (
    <div className="min-h-screen bg-background pb-20 md:pb-0">
      <header className="sticky top-0 z-30 border-b-2 border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Logo className="text-xl" />
          <nav className="hidden items-center gap-1 md:flex">
            {links.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold text-muted-foreground transition hover:bg-muted hover:text-foreground"
                activeProps={{ className: "bg-primary/10 !text-primary" }}
              >
                <l.icon className="h-4 w-4" />
                {l.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            {showPoints && (
              <Link to="/shop" className="duo-chip" title="Your points">
                <Gem className="h-4 w-4 text-primary" />
                {formatPoints(me.user.currency)}
              </Link>
            )}
            <button
              onClick={logout}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>

      {/* Bottom tab bar on phones */}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex justify-around border-t-2 border-border bg-background/95 py-2 backdrop-blur md:hidden">
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className="flex flex-col items-center gap-0.5 rounded-xl px-2 py-1 text-[11px] font-bold text-muted-foreground"
            activeProps={{ className: "!text-primary" }}
          >
            <l.icon className="h-5 w-5" />
            {l.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
