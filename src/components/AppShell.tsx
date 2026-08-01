import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import {
  Shield,
  LayoutDashboard,
  Settings,
  Bell,
  ShoppingBag,
  PlayCircle,
  LogOut,
  Flame,
  Gem,
} from "lucide-react";
import { api, localSession } from "@/lib/api";
export function AppShell({ children, variant }: { children: ReactNode; variant: "guardian" | "individual" | "dependent"}) {
  const nav = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const [points, setUserPoints] = useState(0);
  const [streak, setUserStreak] = useState(0);
  const [session, setSession] = useState<any>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setSession(localSession.get());
   
  }, []);

  useEffect(() => {
    if (!session) {
      //console.error("Session was not found, so streak and currency will default to 0. If there, ignore this error"); 
      return;
    }
  (async () => {

    // Fetch the user
    const u: any = await api.getUser(session?.user_id);
    if (!u) return;

    setUserPoints(u?.currency ?? 0);

    // Fetch or create the session
 
    const sess: any = await api.getOrCreateSession({ 
      user_id: u?.id ?? session?.user_id, 
      guardian_id: session?.guardian_id 
    });
    
    if (!sess) return;
    setUserStreak(sess?.streak ?? 0);
  })();
}, [session]);

  const guardianLinks = [
    { to: "/guardian/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/guardian/settings", label: "Settings", icon: Settings },
    { to: "/guardian/reports", label: "Reports", icon: Bell },
    { to: "/shop", label: "Shop", icon: ShoppingBag },
  ];
  const indivLinks = [
    { to: "/guardian/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/shop", label: "Shop", icon: ShoppingBag },
  ];
  const dependentLinks = [
    { to: "/guardian/dashboard", label: "Dashboard", icon: LayoutDashboard },
    //{ to: "/guardian/reports", label: "Reports", icon: Bell },
    { to: "/shop", label: "Shop", icon: ShoppingBag },
  ];

  // ✔️ Compute links directly based on variant without state setters
  const links = 
    variant === "guardian" 
      ? guardianLinks 
      : variant === "individual" 
      ? indivLinks 
      : dependentLinks;

  function logout() {
    localSession.clear();
    nav({ to: "/" });
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto flex max-w-6xl gap-6 px-4 py-6 md:px-6">
        {/* Sidebar */}
        <aside className="hidden w-56 shrink-0 md:block">
          <Link to="/guardian/dashboard" className="mb-6 flex items-center gap-2 px-2 font-display text-xl font-extrabold">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-primary text-primary-foreground shadow-glow">
              <Shield className="h-5 w-5" />
            </span>
            <span className="bg-gradient-primary bg-clip-text text-transparent">YTG</span>
          </Link>
          <nav className="space-y-1">
            {links.map((l) => {
              const active = pathname === l.to;
              return (
                <Link
                  key={l.to}
                  to={l.to}
                  className={`flex items-center gap-3 rounded-xl border-2 px-3 py-2.5 text-sm font-bold uppercase tracking-wide transition ${
                    active
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : "border-transparent text-muted-foreground hover:border-border hover:bg-card hover:text-foreground"
                  }`}
                >
                  <l.icon className="h-5 w-5" />
                  {l.label}
                </Link>
              );
            })}
            <button
              onClick={logout}
              className="mt-4 flex w-full items-center gap-3 rounded-xl border-2 border-transparent px-3 py-2.5 text-sm font-bold uppercase tracking-wide text-muted-foreground hover:border-border hover:bg-card"
            >
              <LogOut className="h-5 w-5" /> Sign out
            </button>
          </nav>
        </aside>

        {/* Main */}
        <main className="min-w-0 flex-1">
          {/* Top chip bar */}
          <div className="mb-6 flex items-center justify-between gap-3">
            <Link to="/guardian/dashboard" className="flex items-center gap-2 font-display text-lg font-extrabold md:hidden">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-xl bg-gradient-primary text-primary-foreground">
                <Shield className="h-4 w-4" />
              </span>
              <span className="bg-gradient-primary bg-clip-text text-transparent">YTG</span>
            </Link>
            <div className="ml-auto flex items-center gap-2">
              <span className="duo-chip text-warm-foreground">
                <Flame className="h-4 w-4 text-warm" /> {streak.toLocaleString()}
              </span>
              <span className="duo-chip text-primary">
                <Gem className="h-4 w-4" /> {points.toLocaleString()}
              </span>
              {/* Only render client-side user metadata once mounted */}
              {mounted && session?.username && (
                <span className="hidden text-xs text-muted-foreground sm:inline">
                  @{session.username}
                </span>
              )}
            </div>
          </div>

          {/* Mobile bottom nav */}
          <div className="mb-4 flex gap-2 overflow-x-auto md:hidden">
            {links.map((l) => {
              const active = pathname === l.to;
              return (
                <Link
                  key={l.to}
                  to={l.to}
                  className={`inline-flex items-center gap-1.5 rounded-xl border-2 px-3 py-2 text-xs font-bold uppercase ${
                    active
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : "border-border bg-card text-muted-foreground"
                  }`}
                >
                  <l.icon className="h-4 w-4" /> {l.label}
                </Link>
              );
            })}
          </div>

          {children}
        </main>
      </div>
    </div>
  );
}