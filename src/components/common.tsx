import { Link } from "@tanstack/react-router";
import { Loader2, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Knight } from "@/components/game/Knight";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <Link to="/" className={cn("flex items-center gap-2.5", className)} aria-label="YTG home">
      <Knight variant="head" scale={1} />
      <span className="font-display text-sm text-primary">YTG</span>
    </Link>
  );
}

export function FullPageSpinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Spinner label={label} />
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-display text-xl">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  tone = "primary",
}: {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "primary" | "success" | "warm" | "destructive";
}) {
  const tones = {
    primary: "bg-primary/10 text-primary",
    success: "bg-success/15 text-success",
    warm: "bg-warm/30 text-warm-foreground",
    destructive: "bg-destructive/10 text-destructive",
  };
  return (
    <div className="panel p-5">
      <div className="flex items-center gap-3">
        <span
          className={cn("inline-flex h-9 w-9 items-center justify-center rounded-xl", tones[tone])}
        >
          <Icon className="h-5 w-5" />
        </span>
        <span className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
      </div>
      <div className="mt-3 font-display text-xl">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-border px-6 py-10 text-center">
      <Icon className="h-8 w-8 text-muted-foreground" />
      <div className="font-bold">{title}</div>
      {children && <div className="max-w-sm text-sm text-muted-foreground">{children}</div>}
    </div>
  );
}

export function ErrorNotice({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="rounded-2xl border-2 border-destructive/30 bg-destructive/5 p-4 text-sm">
      <div className="font-bold text-destructive">Couldn't load this</div>
      <div className="mt-1 text-muted-foreground">
        {error instanceof Error ? error.message : String(error)}
      </div>
      {onRetry && (
        <button className="mt-3 font-bold text-primary underline" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export const formatPoints = (n: number) => n.toLocaleString();
