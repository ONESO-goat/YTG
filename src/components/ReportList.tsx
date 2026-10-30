import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Trash2 } from "lucide-react";
import { EmptyState, ErrorNotice, Spinner } from "@/components/common";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { keys, toastError, useReports } from "@/lib/queries";

export function ReportList({ guardianId, limit }: { guardianId: string; limit?: number }) {
  const qc = useQueryClient();
  const reports = useReports(guardianId);
  const remove = useMutation({
    mutationFn: (reportId: string) => api.deleteReport(guardianId, reportId),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.reports(guardianId) }),
    onError: toastError,
  });

  if (reports.isPending) return <Spinner label="Loading reports…" />;
  if (reports.isError)
    return <ErrorNotice error={reports.error} onRetry={() => reports.refetch()} />;

  const items = limit ? reports.data.slice(0, limit) : reports.data;
  if (!items.length) {
    return (
      <EmptyState icon={Bell} title="No reports yet">
        When something on screen matches your restrictions, a short report shows up here.
      </EmptyState>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((r) => (
        <li key={r.id} className="panel flex items-start gap-3 p-4">
          <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-nudge text-nudge-foreground">
            <Bell className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
              {r.created_at ? timeAgo(r.created_at) : r.updated_at}
            </div>
            <p className="mt-1 whitespace-pre-line break-words text-sm">{r.content}</p>
          </div>
          <button
            className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-destructive"
            onClick={() => remove.mutate(r.id)}
            disabled={remove.isPending}
            aria-label="Delete report"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </li>
      ))}
    </ul>
  );
}
