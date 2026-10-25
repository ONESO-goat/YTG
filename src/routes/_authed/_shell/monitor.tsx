import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import {
  FlaskConical,
  Gem,
  Leaf,
  Play,
  ShieldAlert,
  Sparkles,
  Square,
  TrendingDown,
  TriangleAlert,
} from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { PageHeader, StatCard, formatPoints } from "@/components/common";
import { RequireRole } from "@/components/RequireRole";
import { Input } from "@/components/ui/input";
import { SCAN_INTERVAL_MS, useMonitor, type MonitorState } from "@/hooks/useMonitor";
import { api } from "@/lib/api";
import { meQueryKey, useMe } from "@/lib/auth";
import {
  ensureNotificationPermission,
  forcePictureInPictureWarning,
  sendWarningNotification,
} from "@/lib/notify";
import { keys, toastError, useHealth, useSettings } from "@/lib/queries";
import type { ScanResult } from "@/lib/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authed/_shell/monitor")({
  component: () => (
    <RequireRole roles={["personal", "member"]}>
      <Monitor />
    </RequireRole>
  ),
});

function Monitor() {
  const me = useMe();
  const qc = useQueryClient();
  const guardian = me.guardian!;
  const settings = useSettings(guardian.id);
  const health = useHealth();
  const [pop, setPop] = useState<{ key: number; amount: number } | null>(null);
  const wasWarning = useRef(false);

  const warningText = settings.data?.warning_message || "Please move away from this content.";
  const applauseText = settings.data?.applause_message || "Proud of you for moving past that!";

  function onResult(r: ScanResult) {
    if (r.flagged && !wasWarning.current) {
      sendWarningNotification({
        body: r.description ? `${warningText} (${r.description})` : warningText,
      });
      if (settings.data?.strictness === "harsh") forcePictureInPictureWarning(warningText);
    }
    if (r.points_awarded > 0) {
      setPop({ key: Date.now(), amount: r.points_awarded });
      if (wasWarning.current) {
        toast.success(`${applauseText} +${r.points_awarded} points`);
        sendWarningNotification({
          title: "YTG: nice work",
          body: `${applauseText} +${r.points_awarded} points`,
          throttleMs: 0,
        });
      }
    }
    if (r.points_lost > 0)
      toast.error(`You stayed on flagged content, so you lost ${r.points_lost} points.`);
    if (r.points_awarded || r.points_lost) {
      qc.setQueryData(meQueryKey, { ...me, user: { ...me.user, currency: r.currency } });
    }
    wasWarning.current = r.warning_active;
  }

  const monitor = useMonitor({
    onResult,
    onStopped: (reason) => {
      toast.message(reason);
      qc.invalidateQueries({ queryKey: meQueryKey });
      qc.invalidateQueries({ queryKey: keys.mySession });
    },
  });

  async function handleStart() {
    if (!(await ensureNotificationPermission())) {
      toast.message("Turn on notifications to get nudges while you're in other tabs.");
    }
    try {
      wasWarning.current = false;
      await monitor.start();
    } catch (err) {
      toastError(err);
    }
  }

  async function handleStop() {
    await monitor.stop();
    qc.invalidateQueries({ queryKey: keys.mySession });
    if (monitor.earned) toast.success(`Session ended. You earned ${monitor.earned} points.`);
  }

  return (
    <>
      <PageHeader title="Session" description={`Guarded by ${guardian.name}`} />

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="relative">
          <StatCard icon={Gem} label="Balance" value={formatPoints(me.user.currency)} />
          {pop && (
            <span
              key={pop.key}
              className="animate-points-pop pointer-events-none absolute right-6 top-6 font-display text-2xl font-extrabold text-success"
            >
              +{pop.amount}
            </span>
          )}
        </div>
        <StatCard
          icon={Sparkles}
          label="Earned this session"
          value={`+${monitor.earned}`}
          tone="success"
        />
        <StatCard
          icon={TrendingDown}
          label="Lost this session"
          value={`-${monitor.lost}`}
          tone="destructive"
        />
      </div>

      <div className="duo-card mt-6 p-8">
        {!monitor.running ? (
          <div className="flex flex-col items-center gap-4 py-8 text-center">
            <Sparkles className="h-10 w-10 text-primary animate-sparkle" />
            <h2 className="font-display text-2xl font-extrabold">Ready when you are</h2>
            <p className="max-w-md text-sm text-muted-foreground">
              YTG will ask to see your screen. Every {SCAN_INTERVAL_MS / 1000} seconds it takes a
              quiet look. Each clean minute earns 10 points, and walking away from a warning earns
              25.
            </p>
            {!guardian.on && (
              <p className="text-sm font-bold text-destructive">
                Monitoring is paused for this guardian.
              </p>
            )}
            <button
              className="duo-btn duo-btn-lg"
              onClick={handleStart}
              disabled={monitor.state === "starting" || !guardian.on}
            >
              <Play className="h-5 w-5" />{" "}
              {monitor.state === "starting" ? "Starting…" : "Start session"}
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-6 py-4 text-center">
            <StatusPanel state={monitor.state} warningText={warningText} />
            <button className="duo-btn duo-btn-outline" onClick={handleStop}>
              <Square className="h-4 w-4" /> Stop session
            </button>
          </div>
        )}
      </div>

      {monitor.log.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-3 font-display text-xl font-extrabold">Activity</h2>
          <ul className="duo-card divide-y-2 divide-border">
            {monitor.log.slice(0, 10).map((entry) => (
              <li
                key={entry.at}
                className="flex items-center justify-between gap-3 px-4 py-3 text-sm"
              >
                <span className="flex min-w-0 items-center gap-2">
                  {entry.flagged ? (
                    <TriangleAlert className="h-4 w-4 shrink-0 text-warm-foreground" />
                  ) : (
                    <Leaf className="h-4 w-4 shrink-0 text-success" />
                  )}
                  <span className="truncate">
                    {entry.analysis_failed
                      ? "Couldn't analyze this screen"
                      : entry.flagged
                        ? `Flagged: ${entry.category ?? entry.description}`
                        : entry.warning_active
                          ? "Moved away, keep going"
                          : "All clear"}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-3">
                  {entry.points_awarded > 0 && (
                    <span className="font-bold text-success">+{entry.points_awarded}</span>
                  )}
                  {entry.points_lost > 0 && (
                    <span className="font-bold text-destructive">-{entry.points_lost}</span>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {new Date(entry.at).toLocaleTimeString()}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {health.data?.ai_backend === "stub" && <DevPanel />}

      <p className="mt-6 text-center text-xs text-muted-foreground">
        You can stop the session any time. YTG never watches without your consent.
      </p>
    </>
  );
}

function StatusPanel({ state, warningText }: { state: MonitorState; warningText: string }) {
  if (state === "warning") {
    return (
      <div className="w-full rounded-2xl bg-warm/40 p-6 text-warm-foreground">
        <ShieldAlert className="mx-auto h-10 w-10" />
        <div className="mt-3 font-display text-2xl font-extrabold">A gentle nudge</div>
        <p className="mt-2 text-sm">{warningText}</p>
        <p className="mt-2 text-xs opacity-80">
          Move away now to earn a bonus. Staying may cost points.
        </p>
      </div>
    );
  }
  if (state === "recovering") {
    return (
      <div className="w-full rounded-2xl bg-success/15 p-6">
        <Leaf className="mx-auto h-10 w-10 text-success" />
        <div className="mt-3 font-display text-2xl font-extrabold">Nice, you moved on</div>
        <p className="mt-2 text-sm text-muted-foreground">
          Stay away a little longer to collect your bonus.
        </p>
      </div>
    );
  }
  return (
    <div>
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success/15">
        <span className="h-4 w-4 animate-soft-pulse rounded-full bg-success" />
      </div>
      <div className="mt-4 font-display text-2xl font-extrabold">All good. Keep going.</div>
      <p className="mt-1 text-sm text-muted-foreground">
        Checking every {SCAN_INTERVAL_MS / 1000} seconds.
      </p>
    </div>
  );
}

/** Only shown while the backend runs with AI_BACKEND=stub. */
function DevPanel() {
  const [category, setCategory] = useState("hate speech");
  const [busy, setBusy] = useState(false);

  async function simulate(scans: number) {
    setBusy(true);
    try {
      const r = await api.simulate(category, scans);
      toast.message(
        scans
          ? `Next ${r.remaining} scans will be flagged as “${r.category}”`
          : "Simulation cleared",
      );
    } catch (err) {
      toastError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={cn("mt-6 rounded-2xl border-2 border-dashed border-primary/40 p-5")}>
      <div className="flex items-center gap-2 font-bold">
        <FlaskConical className="h-5 w-5 text-primary" /> Developer mode (AI is stubbed)
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Scans always come back clean unless you simulate flagged content. Keep the screen changing
        (scroll or switch tabs), because an unchanged screen pauses the session after ~30 seconds.
      </p>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <Input
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Category to simulate"
        />
        <button className="duo-btn shrink-0" disabled={busy} onClick={() => simulate(3)}>
          Flag next 3 scans
        </button>
        <button className="duo-btn shrink-0" disabled={busy} onClick={() => simulate(10)}>
          Flag next 10
        </button>
        <button
          className="duo-btn duo-btn-outline shrink-0"
          disabled={busy}
          onClick={() => simulate(0)}
        >
          Clear
        </button>
      </div>
    </section>
  );
}
