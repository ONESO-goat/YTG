import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { api, localSession } from "@/lib/api";
import { toast } from "sonner";
import { Users, Activity, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/guardian/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — YTG" }] }),
  component: Dashboard,
});

function Dashboard() {
  const nav = useNavigate();
  const [monitoringOn, setMonitoringOn] = useState(false);
  const [isPersonalAccount, setIsPersonalAccount] = useState(false);
  const [isDependent, setIsDependent] = useState(false);
  const [connections, setConnections] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);

  // 1. Keep session state stable between renders
  const [session, setSession] = useState<any>(null);

  // 2. Safely read localStorage ONLY on the client after mount
  useEffect(() => {
    const activeSession = localSession.get();
    if (!activeSession) {
      nav({ to: "/auth" });
      return;
    }
    setSession(activeSession);
  }, [nav]);

  // 3. Fetch data only when guardian_id is available
  const guardianId = session?.guardian_id;

  useEffect(() => {
    if (!guardianId) return;

    (async () => {
      try {
        const guar = await api.getGuardian(guardianId);
        if (monitoringOn === false && guar.on) {toggleMonitoring(true)} 
        //else {toggleMonitoring(false)}
        setIsPersonalAccount(guar.guardian_type === "personal")
        setIsDependent(guar?.guardian_type==="dependent");
        const c: any = await api.connections(guardianId);
        setConnections(Array.isArray(c) ? c : c?.connections || []);
      } catch {}
      
      try {
        const r: any = await api.reports(guardianId);
        setReports(Array.isArray(r) ? r : r?.reports || []);
      } catch {}
    })();
  }, [guardianId]); // ✅ Only re-runs if guardianId actually changes!

  async function toggleMonitoring(v: boolean) {
    if (!session?.guardian_id) return;
    setMonitoringOn(v);
    try {
      if (v) await api.guardianOn(session.guardian_id);
      else await api.guardianOff(session.guardian_id);
      toast.success(v ? "Guardian is on" : "Guardian paused");
    } catch {
      toast.warning("Backend unreachable");
    }
  }
  return (
    <AppShell variant="guardian">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold">Household overview</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Everything happening under your Guardian, at a glance.
          </p>
        </div>



        {(!isPersonalAccount && !isDependent) && (<div className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
          <div>
            <div className="text-xs text-muted-foreground">Monitoring</div>
            <div className="font-medium">{monitoringOn ? "Active" : "Paused"}</div>
          </div>
          <Switch checked={monitoringOn} onCheckedChange={toggleMonitoring} />
        </div>)}

      </div>



      <div className="mt-8 grid gap-6 md:grid-cols-2">

        { (!isDependent) && (<section className="rounded-2xl border border-border bg-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-semibold">

              <Users className="h-4 w-4 text-primary" /> {!isPersonalAccount ? 'Connected people' : "Settings"}
              
            </h2>
            <Link to="/guardian/settings">
              <Button variant="ghost" size="sm">
                Manage <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </div>
          {connections.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {(!isPersonalAccount && !isDependent) ? 'No one connected yet. Add a dependent from Settings.' : "Customize guardian function"}
            </p>
          ) : (
            <ul className="space-y-2">
              {connections.map((c: any, i: number) => (
                <li
                  key={c.user_id || i}
                  className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-sm"
                >
                  <span>{c.username || c.user_name || c.user_id}</span>
                  <span className="text-xs text-muted-foreground">{c.relationship || "connected"}</span>
                </li>
              ))}
            </ul>
          )}
        </section>)}

        <section className="rounded-2xl border border-border bg-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-semibold">
              <Activity className="h-4 w-4 text-primary" /> Recent activity
            </h2>
            <Link to="/guardian/reports">
              <Button variant="ghost" size="sm">
                All reports <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </div>
          {(!isDependent) &&
          (reports.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing to report — that's a good sign.</p>
          ) : (
            <ul className="space-y-2">
              {reports.slice(0, 5).map((r: any, i: number) => (
                <li key={i} className="rounded-lg bg-muted/50 px-3 py-2 text-sm">
                  <div className="font-medium">{r.description || "Flagged event"}</div>
                  <div className="text-xs text-muted-foreground">
                    {r.timestamp || r.created_at || ""}
                  </div>
                </li>
              ))}
            </ul>
          ))
          }
        </section>
      </div>

      <div className="mt-6 rounded-2xl border border-dashed border-border bg-card/60 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-medium">Want to try a live monitoring session?</div>
            <p className="text-sm text-muted-foreground">
              Open the individual view to grant screen share and see the 5-second loop.
            </p>
          </div>
          <Link to="/guardian/monitor">
            <Button variant="outline">Open session view</Button>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
