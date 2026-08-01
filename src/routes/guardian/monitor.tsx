import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useScanLoop } from "@/hooks/useScanLoop";
import type { ScanResult } from "@/lib/types";
import { ensureNotificationPermission, sendWarningNotification } from "@/lib/notify";
import { Button } from "@/components/ui/button";
import { api, localSession } from "@/lib/api";
import { toast } from "sonner";
import { Play, Square, Sparkles, ShieldAlert, Trophy, Flame } from "lucide-react";

export const Route = createFileRoute("/guardian/monitor")({
  head: () => ({ meta: [{ title: "Session — YTG" }] }),
  component: Monitor,
});

function Monitor() {
  const nav = useNavigate();
  const [points, setPoints] = useState(0);
  const [streak, setStreak] = useState(0);
  const [guardianSession, setGuardianSession] = useState();
  const [pointsPop, setPointsPop] = useState(0);
  const [applauding, setApplauding] = useState(false);
  const [isHarsh, setIsHarsh] = useState(false);
  const [guardianMsgs, setGuardianMsgs] = useState({
    warning: "Please skip this one for me, okay?",
    applause: "Proud of you for moving past that ❤️",
  });

  const session = typeof window !== "undefined" ? localSession.get() : null;

  useEffect(() => {
  (async () => {
   
    
    if (!session) {
      nav({ to: "/auth" });
    } else {
      const u: any = await api.getUser(session?.user_id);
      if (u){
        console.log(`THE USERS POINTS: ${u.currency}`);
        setPoints(u.currency || 0);}
    }
  })();
}, [session, nav]);

  useEffect(() => {
    (async () => {
      if (!session?.guardian_id) return;
      try {
        //console.log(`USER ID: ${session?.user_id} GUARDIAN ID: ${session?.guardian_id} SESSION id: ${session?.id}`)
        const u: any = await api.getUser(session.user_id);
        const s: any = await api.getSettings(session.guardian_id);
        
        setGuardianMsgs((prev) => ({
          warning: s?.custom_warning_messages?.warning || prev.warning,
          applause: s?.custom_warning_messages?.applause || prev.applause,
        }));
        setIsHarsh(s?.strictness === "harsh");
      } catch {}
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleResult(r: ScanResult) {
    if (r.warning_active) {
      sendWarningNotification({
        body: r.description
          ? `${guardianMsgs.warning} (detected: ${r.description})`
          : guardianMsgs.warning,
      });
    }
    if (r.points_awarded) {
      setApplauding(true);
      setPoints((p) => p + 10);
      setStreak((s) => s + 1);
      setPointsPop((n) => n + 1);
      if (session) api.addPoints(session.user_id, 10).catch(() => {});
      setTimeout(() => setApplauding(false), 2200);
    }
  }

  const { start, stop, running, lastResult, state} = useScanLoop(null, 5000, guardianMsgs, isHarsh)
//   const { videoRef, canvasRef, start, stop, running, state, description } = useScanLoop({
//     userId: session?.user_id || "",
//     guardianId: session?.guardian_id || session?.user_id || "",
//     intervalMs: 5000,
//     onResult: handleResult,
//   });


  async function handleStart() {
    try {


      const granted = await ensureNotificationPermission();
      if (!granted) {
        toast.message("Enable notifications to get alerts outside this tab.");
      }

        const gS: any = await api.startSession(
            {user_id: session?.user_id!, guardian_id: session?.guardian_id!}
        )
        if (!gS) return;
        console.log(gS?.id);
      await start(gS?.id || null);
    } catch (e) {
      toast.error(`Screen share is required to start a session: ${e}`);
    }
  }

  async function handleStop() {
    try {


        const gS: any = await api.stopSession(
            {user_id: session?.user_id!, guardian_id: session?.guardian_id!}
        )

      stop();
    } catch (e) {
      toast.error(`Error trying to stop session: ${e}`);
    }
  }

  const displayState = applauding ? "applause" : state;

  return (
    <AppShell variant="individual">
      <div className="grid gap-6 md:grid-cols-3">
        <div className="rounded-2xl border border-border bg-card p-6">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Points</div>
          <div className="relative mt-2 font-display text-4xl font-semibold">
            {points.toLocaleString()}
            {pointsPop > 0 && (
              <span
                key={pointsPop}
                className="animate-points-pop absolute -right-2 top-0 text-lg font-semibold text-success"
              >
                +10
              </span>
            )}
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-6">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
            <Flame className="h-3 w-3" /> Streak
          </div>
          <div className="mt-2 font-display text-4xl font-semibold">{streak}</div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-6">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">Session</div>
          <div className="mt-2 flex items-center gap-2 font-medium">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                running ? "bg-success animate-soft-pulse" : "bg-muted-foreground/40"
              }`}
            />
            {running ? "Watching" : "Paused"}
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-border bg-card p-8">
        {!running ? (
          <div className="flex flex-col items-center gap-4 py-8 text-center">
            <Sparkles className="h-8 w-8 text-primary" />
            <h2 className="font-display text-2xl">Ready when you are</h2>
            <p className="max-w-md text-sm text-muted-foreground">
              YTG will ask permission to view your screen. Every 5 seconds it takes a quiet look and
              cheers you on when you keep good habits.
            </p>
            <Button size="lg" onClick={handleStart}>
              <Play className="mr-2 h-4 w-4" /> Start session
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 py-6 text-center">
            {displayState === "clear" && (
              <>
                <div className="text-4xl">✨</div>
                <div className="font-display text-xl">All good. Keep going.</div>
                <p className="text-sm text-muted-foreground">Checking every 5 seconds.</p>
              </>
            )}
            {displayState === "cooldown" && (
              <>
                <div className="text-4xl">🌿</div>
                <div className="font-display text-xl">Nice — you moved on.</div>
                <p className="text-sm text-muted-foreground">Confirming a full 5 seconds…</p>
              </>
            )}
            {displayState === "applause" && (
              <div className="rounded-2xl bg-success/15 px-6 py-6">
                <Trophy className="mx-auto h-8 w-8 text-success" />
                <div className="mt-3 font-display text-2xl">+10 points</div>
                <p className="mt-1 text-sm text-success-foreground">{guardianMsgs.applause}</p>
              </div>
            )}
            {displayState === "warning" && (
              <div className="w-full rounded-2xl bg-warm/40 p-6 text-warm-foreground">
                <ShieldAlert className="mx-auto h-8 w-8" />
                <div className="mt-3 font-display text-2xl">A gentle nudge</div>
                <p className="mt-2 text-sm">{guardianMsgs.warning}</p>
                {guardianMsgs && (
                  <p className="mt-2 text-xs opacity-80">{guardianMsgs.warning}</p>
                )}
              </div>
            )}

            <Button variant="outline" onClick={handleStop}>
              <Square className="mr-2 h-4 w-4" /> Stop session
            </Button>
          </div>
        )}
        {/* <video ref={videoRef} className="hidden" muted playsInline />
        <canvas ref={canvasRef} className="hidden" /> */}
      </div>

      <p className="mt-4 text-center text-xs text-muted-foreground">
        You can stop the session any time — YTG never watches without your consent.
      </p>
    </AppShell>
  );
}
