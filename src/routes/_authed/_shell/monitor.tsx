import { useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { FlaskConical, Leaf, Play, Square, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { PageHeader, formatPoints } from "@/components/common";
import { useCelebrate } from "@/components/game/Celebrations";
import { Knight, type KnightMood } from "@/components/game/Knight";
import { GoalRing } from "@/components/game/widgets";
import { Progress as Bar } from "@/components/ui/progress";
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
import {
  keys,
  toastError,
  useHealth,
  useProgress,
  useRefreshProgress,
  useSettings,
} from "@/lib/queries";
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
  const progress = useProgress();
  const celebrate = useCelebrate();
  const refreshProgress = useRefreshProgress();
  const [pop, setPop] = useState<{ key: number; amount: number; xp: number } | null>(null);
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
      setPop({ key: Date.now(), amount: r.points_awarded, xp: r.xp_awarded });
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
      refreshProgress();
    }
    celebrate(r.events);
    wasWarning.current = r.warning_active;
  }

  const monitor = useMonitor({
    onResult,
    onStarted: celebrate,
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

      <Stage
        state={monitor.state === "starting" ? "starting" : monitor.running ? monitor.state : "idle"}
        warningText={warningText}
        guardianOn={guardian.on}
        pop={pop}
        onStart={handleStart}
        onStop={handleStop}
      />

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {progress.data && (
          <div className="panel flex items-center gap-4 p-4">
            <GoalRing
              value={progress.data.today.clean_minutes}
              goal={progress.data.today.goal_minutes}
              size={72}
            />
            <div className="min-w-0 text-sm">
              <div className="font-semibold">Daily goal</div>
              <div className="mt-1 text-xs text-muted-foreground">
                {progress.data.today.minute_points >= progress.data.today.minute_points_cap
                  ? "Minute-points cap reached. Bonuses still count."
                  : progress.data.today.goal_completed
                    ? "Done for today!"
                    : `${progress.data.today.goal_minutes - progress.data.today.clean_minutes} clean minutes to go`}
              </div>
            </div>
          </div>
        )}
        {progress.data && (
          <div className="panel p-4">
            <div className="flex items-baseline justify-between">
              <span className="font-display text-[10px] text-primary">
                Lv {progress.data.level}
              </span>
              <span className="text-xs text-muted-foreground">{progress.data.title}</span>
            </div>
            <Bar
              className="mt-3 h-3"
              value={(progress.data.xp_into_level / progress.data.xp_for_next_level) * 100}
            />
            <div className="mt-2 text-xs text-muted-foreground">
              {progress.data.xp_into_level} / {progress.data.xp_for_next_level} XP
            </div>
          </div>
        )}
        <div className="panel grid grid-cols-3 gap-2 p-4 text-center">
          <div>
            <div className="text-[11px] text-muted-foreground">Balance</div>
            <div className="mt-2 font-display text-xs">{formatPoints(me.user.currency)}</div>
          </div>
          <div>
            <div className="text-[11px] text-muted-foreground">Earned</div>
            <div className="mt-2 font-display text-xs text-success">+{monitor.earned}</div>
          </div>
          <div>
            <div className="text-[11px] text-muted-foreground">Lost</div>
            <div className="mt-2 font-display text-xs text-destructive">-{monitor.lost}</div>
          </div>
        </div>
      </div>

      {monitor.log.length > 0 && (
        <section className="mt-6">
          <h2 className="mb-3 font-display text-base">Activity</h2>
          <ul className="panel divide-y-2 divide-border">
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
                          : entry.idle
                            ? "Screen unchanged"
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

// Mirrors IGNORE_THRESHOLD_SECONDS and AVOIDANCE_SECONDS in services/session_services.py
const IGNORE_SECONDS = 30;
const AVOID_SECONDS = 15;

type StageState = MonitorState | "idle";

const STAGE: Record<StageState, { mood: KnightMood; title: string; tone: string; border: string }> =
  {
    idle: { mood: "calm", title: "Ready when you are", tone: "text-foreground", border: "" },
    starting: { mood: "calm", title: "Getting ready…", tone: "text-foreground", border: "" },
    clear: { mood: "calm", title: "All clear", tone: "text-foreground", border: "" },
    still: { mood: "sleepy", title: "Still there?", tone: "text-muted-foreground", border: "" },
    warning: {
      mood: "alert",
      title: "Let's skip this one",
      tone: "text-warm",
      border: "border-warm bg-[#1a0a16]",
    },
    recovering: {
      mood: "happy",
      title: "Nice! Keep going",
      tone: "text-success",
      border: "border-success/60",
    },
  };

/** Seconds since `active` last became true, ticking once a second. */
function useSecondsSince(active: boolean) {
  const [since, setSince] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    setSince(active ? Date.now() : null);
    if (!active) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [active]);
  return since === null ? 0 : Math.max(0, Math.floor((now - since) / 1000));
}

function Countdown({
  seconds,
  total,
  label,
  color,
}: {
  seconds: number;
  total: number;
  label: string;
  color: string;
}) {
  const left = Math.max(total - seconds, 0);
  return (
    <div className="mx-auto mt-6 w-full max-w-sm">
      <div className="h-3 overflow-hidden rounded-sm bg-muted">
        <div
          className={cn("h-full transition-[width] duration-1000 ease-linear", color)}
          style={{ width: `${(left / total) * 100}%` }}
        />
      </div>
      <div className="mt-2 text-xs text-muted-foreground">{label.replace("{s}", String(left))}</div>
    </div>
  );
}

function Stage({
  state,
  warningText,
  guardianOn,
  pop,
  onStart,
  onStop,
}: {
  state: StageState;
  warningText: string;
  guardianOn: boolean;
  pop: { key: number; amount: number; xp: number } | null;
  onStart: () => void;
  onStop: () => void;
}) {
  const s = STAGE[state];
  const warningFor = useSecondsSince(state === "warning");
  const awayFor = useSecondsSince(state === "recovering");
  const running = state !== "idle" && state !== "starting";

  return (
    <div
      className={cn("panel relative flex flex-col items-center px-6 py-10 text-center", s.border)}
    >
      <div className="relative">
        <Knight mood={s.mood} scale={3} animate={running || state === "idle"} />
        {pop && (
          <span
            key={pop.key}
            className="animate-points-pop pointer-events-none absolute -right-10 top-4 font-display text-sm text-gold"
          >
            +{pop.amount}
          </span>
        )}
      </div>

      <h2 className={cn("mt-8 text-base leading-relaxed sm:text-lg", s.tone)}>{s.title}</h2>

      {state === "idle" && (
        <>
          <p className="mt-3 max-w-md text-sm text-muted-foreground">
            Your knight will ask to see your screen and take a quiet look every{" "}
            {SCAN_INTERVAL_MS / 1000} seconds. Clean minutes earn points, and walking away from a
            warning earns a bonus.
          </p>
          {!guardianOn && (
            <p className="mt-3 text-sm font-semibold text-destructive">
              Monitoring is paused for this guardian.
            </p>
          )}
          <button className="btn btn-lg mt-8" onClick={onStart} disabled={!guardianOn}>
            <Play className="h-4 w-4" /> Start session
          </button>
        </>
      )}

      {state === "clear" && (
        <p className="mt-3 text-sm text-muted-foreground">
          Your knight is on watch. Every clean minute earns 10 points.
        </p>
      )}

      {state === "still" && (
        <p className="mt-3 max-w-md text-sm text-muted-foreground">
          Your screen hasn't changed, so points are paused until it does. After about 5 minutes the
          session stops by itself.
        </p>
      )}

      {state === "warning" && (
        <>
          <p className="mt-3 max-w-md text-sm text-warm-foreground">{warningText}</p>
          {warningFor < IGNORE_SECONDS ? (
            <Countdown
              seconds={warningFor}
              total={IGNORE_SECONDS}
              label="{s}s to walk away for a bonus"
              color="bg-warm"
            />
          ) : (
            <p className="mt-6 font-display text-[10px] leading-relaxed text-warm">
              Staying here is costing points
            </p>
          )}
        </>
      )}

      {state === "recovering" && (
        <Countdown
          seconds={awayFor}
          total={AVOID_SECONDS}
          label="Stay away {s}s more to collect +25"
          color="bg-success"
        />
      )}

      {running && (
        <button className="btn btn-outline mt-8" onClick={onStop}>
          <Square className="h-4 w-4" /> Stop session
        </button>
      )}
    </div>
  );
}

/** Only shown while the backend runs with AI_BACKEND=stub. */
function DevPanel() {
  const [category, setCategory] = useState("hate speech");
  const [busy, setBusy] = useState(false);
  const celebrate = useCelebrate();
  const refreshProgress = useRefreshProgress();

  async function grant(points: number, xp: number) {
    setBusy(true);
    try {
      const r = await api.grant(points, xp);
      refreshProgress();
      celebrate(r.events);
      toast.message(`Granted ${points ? `${points} points` : `${xp} XP`}`);
    } catch (err) {
      toastError(err);
    } finally {
      setBusy(false);
    }
  }

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
        (scroll or switch tabs), because an unchanged screen earns nothing (and stops the session
        after ~5 minutes).
      </p>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <Input
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          aria-label="Category to simulate"
        />
        <button className="btn shrink-0" disabled={busy} onClick={() => simulate(3)}>
          Flag next 3 scans
        </button>
        <button className="btn shrink-0" disabled={busy} onClick={() => simulate(10)}>
          Flag next 10
        </button>
        <button className="btn btn-outline shrink-0" disabled={busy} onClick={() => simulate(0)}>
          Clear
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <button className="btn btn-outline" disabled={busy} onClick={() => grant(0, 100)}>
          +100 XP
        </button>
        <button className="btn btn-outline" disabled={busy} onClick={() => grant(1000, 0)}>
          +1,000 points
        </button>
      </div>
    </section>
  );
}
