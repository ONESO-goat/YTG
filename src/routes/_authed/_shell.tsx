import { Navigate, Outlet, createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { homePath, useMe } from "@/lib/auth";

export const Route = createFileRoute("/_authed/_shell")({
  component: ShellLayout,
});

function ShellLayout() {
  const me = useMe();
  // Users who haven't finished setup go back to onboarding / waiting
  if (!me.guardian) return <Navigate to={homePath(me)} />;
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
