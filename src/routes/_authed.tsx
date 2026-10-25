import { Navigate, Outlet, createFileRoute } from "@tanstack/react-router";
import { FullPageSpinner } from "@/components/common";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/_authed")({
  component: AuthedLayout,
});

function AuthedLayout() {
  const { status } = useAuth();
  if (status === "loading") return <FullPageSpinner />;
  if (status === "anonymous") return <Navigate to="/auth" search={{ mode: "login" }} />;
  return <Outlet />;
}
