import { Link } from "@tanstack/react-router";
import {
  Bell,
  Flame,
  Gem,
  LayoutDashboard,
  LogOut,
  PlayCircle,
  Settings,
  ShoppingBag,
  Trophy,
  UserCircle,
} from "lucide-react";
import type { ReactNode } from "react";
import { formatPoints, Logo } from "@/components/common";
import { useAuth, useMe } from "@/lib/auth";
import { useProgress } from "@/lib/queries";
import { roleOf, type Role } from "@/lib/roles";
import { cn } from "@/lib/utils";

const NAV: { to: string; label: string; icon: typeof Bell; roles: Role[] }[] = [
  {
    to: "/dashboard",
    label: "Home",
    icon: LayoutDashboard,
    roles: ["personal", "family-owner", "member"],
  },
  { to: "/monitor", label: "Session", icon: PlayCircle, roles: ["personal", "member"] },
  {
    to: "/progress",
    label: "Progress",
    icon: Trophy,
    roles: ["personal", "family-owner", "member"],
  },
  { to: "/shop", label: "Shop", icon: ShoppingBag, roles: ["personal", "member"] },
  { to: "/reports", label: "Reports", icon: Bell, roles: ["personal", "family-owner"] },
  { to: "/settings", label: "Settings", icon: Settings, roles: ["personal", "family-owner"] },
];

export function AppShell({ children }: { children: ReactNode }) {
  const me = useMe();
  const { logout } = useAuth();
  const role = roleOf(me);
  const links = NAV.filter((l) => l.roles.includes(role));
  const playing = role !== "family-owner";
  const progress = useProgress(playing);
  const streak = progress.data?.streak;

  return (
    <div className="min-h-screen bg-background pb-20 md:pb-0">
      <header className="sticky top-0 z-30 border-b-2 border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <Logo className="text-xl" />
          <nav className="hidden items-center gap-1 lg:flex">
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
          <div className="flex items-center gap-1.5 sm:gap-2">
            {playing && progress.data && (
              <>
                <Link
                  to="/progress"
                  className="duo-chip hidden sm:inline-flex"
                  title={`Level ${progress.data.level}: ${progress.data.title}`}
                >
                  <span className="rounded-md bg-gradient-primary px-1.5 text-xs font-extrabold text-primary-foreground">
                    {progress.data.level}
                  </span>
                  {progress.data.title}
                </Link>
                <Link
                  to="/dashboard"
                  className={cn("duo-chip", streak?.at_risk && "border-warm")}
                  title={
                    streak?.at_risk ? "Finish today's goal to keep your streak" : "Your streak"
                  }
                >
                  <Flame
                    className={cn(
                      "h-4 w-4",
                      streak && streak.current > 0 ? "text-orange-500" : "text-muted-foreground",
                    )}
                  />
                  {streak?.current ?? 0}
                </Link>
              </>
            )}
            {playing && (
              <Link to="/shop" className="duo-chip" title="Your points">
                <Gem className="h-4 w-4 text-primary" />
                {formatPoints(me.user.currency)}
              </Link>
            )}
            <Link
              to="/account"
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground"
              activeProps={{ className: "bg-primary/10 !text-primary" }}
              title="Account"
              aria-label="Account"
            >
              <UserCircle className="h-5 w-5" />
            </Link>
            <button
              onClick={logout}
              className="hidden h-9 w-9 items-center justify-center rounded-xl text-muted-foreground hover:bg-muted hover:text-foreground sm:inline-flex"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>

      {/* Bottom tab bar on phones and tablets */}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex justify-around border-t-2 border-border bg-background/95 py-2 backdrop-blur lg:hidden">
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
