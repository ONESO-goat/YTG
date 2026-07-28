import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, localSession } from "@/lib/api";
import { Bell } from "lucide-react";

export const Route = createFileRoute("/guardian/reports")({
  head: () => ({ meta: [{ title: "Reports — YTG" }] }),
  component: Reports,
});

function Reports() {
  const nav = useNavigate();
  const [reports, setReports] = useState<any[]>([]);

  // 1. Keep session state stable across renders
  const [session, setSession] = useState<any>(null);

  // 2. Read localStorage safely on the client post-mount
  useEffect(() => {
    const activeSession = localSession.get();
    if (!activeSession) {
      nav({ to: "/auth" });
      return;
    }
    setSession(activeSession);
  }, [nav]);

  // 3. Extract primitive string dependency
  const guardianId = session?.guardian_id;

  // 4. Fetch reports only when guardianId changes
  useEffect(() => {
    if (!guardianId) return;

    (async () => {
      try {
        const r: any = await api.reports(guardianId);
        setReports(Array.isArray(r) ? r : r?.reports || []);
      } catch {}
    })();
  }, [guardianId]); // ✅ Only fires once when guardianId is set

  return (
    <AppShell variant="guardian">
      <h1 className="font-display text-3xl font-semibold">Alerts</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Flagged events across your household.
      </p>

      <div className="mt-6 divide-y divide-border rounded-2xl border border-border bg-card">
        {reports.length === 0 ? (
          <div className="flex flex-col items-center gap-2 p-12 text-center text-muted-foreground">
            <Bell className="h-8 w-8 opacity-40" />
            <p className="text-sm">No reports yet.</p>
          </div>
        ) : (
          reports.map((r: any, i: number) => (
            <div key={i} className="p-4">
              <div className="flex items-center justify-between">
                <div className="font-medium">{r.description || "Flagged event"}</div>
                <div className="text-xs text-muted-foreground">
                  {r.timestamp || r.created_at || ""}
                </div>
              </div>
              {r.user_id && (
                <div className="mt-1 text-xs text-muted-foreground">for {r.user_id}</div>
              )}
            </div>
          ))
        )}
      </div>
    </AppShell>
  );
}