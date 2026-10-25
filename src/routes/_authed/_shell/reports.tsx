import { createFileRoute } from "@tanstack/react-router";
import { PageHeader } from "@/components/common";
import { ReportList } from "@/components/ReportList";
import { RequireRole } from "@/components/RequireRole";
import { useMe } from "@/lib/auth";

export const Route = createFileRoute("/_authed/_shell/reports")({
  component: () => (
    <RequireRole roles={["personal", "family-owner"]}>
      <Reports />
    </RequireRole>
  ),
});

function Reports() {
  const me = useMe();
  return (
    <>
      <PageHeader
        title="Reports"
        description="Short, neutral summaries of flagged screens. Screenshots themselves are never stored."
      />
      <ReportList guardianId={me.guardian!.id} />
    </>
  );
}
