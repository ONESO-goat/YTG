import { useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, createFileRoute } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { CelebrationProvider } from "@/components/game/Celebrations";
import { api } from "@/lib/api";
import { homePath, useMe } from "@/lib/auth";
import { keys, useProgress } from "@/lib/queries";
import { roleOf } from "@/lib/roles";

export const Route = createFileRoute("/_authed/_shell")({
  component: ShellLayout,
});

function ShellLayout() {
  const me = useMe();
  // Users who haven't finished setup go back to onboarding / waiting
  if (!me.guardian) return <Navigate to={homePath(me)} />;
  return (
    <CelebrationProvider>
      <TimezoneSync enabled={roleOf(me) !== "family-owner"} />
      <AppShell>
        <Outlet />
      </AppShell>
    </CelebrationProvider>
  );
}

/** Days, goals and streaks follow the user's local calendar, so tell the server where they are. */
function TimezoneSync({ enabled }: { enabled: boolean }) {
  const qc = useQueryClient();
  const progress = useProgress(enabled);
  const serverTz = progress.data?.timezone;

  useEffect(() => {
    if (!serverTz) return;
    let local: string;
    try {
      local = Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch {
      return;
    }
    if (!local || local === serverTz) return;
    api
      .updatePreferences({ timezone: local })
      .then((p) => qc.setQueryData(keys.progress, p))
      .catch(() => {
        /* unknown zone on the server: keep using its current one */
      });
  }, [serverTz, qc]);

  return null;
}
