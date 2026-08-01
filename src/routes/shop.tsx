import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, localSession } from "@/lib/api";
import { toast } from "sonner";
import { Gift, Sparkles, Trophy, Flame, Gem } from "lucide-react";

export const Route = createFileRoute("/shop")({
  head: () => ({ meta: [{ title: "Shop — YTG" }] }),
  component: Shop,
});

const FALLBACK = [
  { id: "r1", name: "$5 Gift Card of your choice!", reward_amount: 5, reward_cost: 31000, reward_type: "gift_card" },
  { id: "r2", name: "$25 Gift Card of your choice!", reward_amount: 25, reward_cost: 182000, reward_type: "gift_card" },
  { id: "r3", name: "$100 Gift Card of your choice!", reward_amount: 100, reward_cost: 364000, reward_type: "gift_card" },
  { id: "r4", name: "Streak freeze", reward_amount: 0, reward_cost: 5000, reward_type: "streak_freeze" },
  { id: "r5", name: "Extra screen time (30 min)", reward_amount: 30, reward_cost: 400, reward_type: "custom" },
];

function Shop() {
  const nav = useNavigate();
  const [rewards, setRewards] = useState<any[]>([]);
  const [points, setPoints] = useState(0);

  // 1. Keep session state stable across renders
  const [session, setSession] = useState<any>(null);

  // 2. Read localSession SAFELY on the client after mount
  useEffect(() => {
    const activeSession = localSession.get();
    if (!activeSession) {
      nav({ to: "/auth" });
      return;
    }
    setSession(activeSession);
    setPoints(activeSession.points || 0);
  }, [nav]);

  // 3. Fetch rewards list once mounted
  useEffect(() => {
    if (!session) return;

    (async () => {
      try {
        const r: any = await api.listRewards();
        const list = Array.isArray(r) ? r : r?.rewards || [];
        setRewards(list.length ? list : FALLBACK);
      } catch {
        setRewards(FALLBACK);
      }
    })();
  }, [session?.user_id]); // ✅ Only re-run if user_id changes

  async function buy(rw: any) {
    const id = rw.id || rw.reward_id;
    if (points < rw.reward_cost) {
      toast.error("Not enough points yet — keep going.");
      return;
    }
    try {
      if (session?.user_id) await api.buyReward(session.user_id, id);
    } catch {}
    const newPoints = points - rw.reward_cost;
    setPoints(newPoints);
    localSession.patch({ points: newPoints });
    toast.success(`Redeemed: ${rw.name}`);
  }

  const nextReward = [...rewards].sort((a, b) => a.reward_cost - b.reward_cost).find((r) => r.reward_cost > points);
  const progress = nextReward ? Math.min(100, Math.round((points / nextReward.reward_cost) * 100)) : 100;
  const level = Math.max(1, Math.floor(points / 500) + 1);
  const variant = session?.role === "guardian" ? "guardian" : "individual";

  return (
    <AppShell variant={variant}>
      <div className="relative overflow-hidden rounded-3xl border-2 border-primary/30 bg-gradient-primary p-6 text-primary-foreground shadow-glow">
        <Sparkles className="animate-sparkle absolute right-6 top-4 h-5 w-5 opacity-70" />
        <Sparkles className="animate-sparkle absolute right-16 top-10 h-3 w-3 opacity-60" style={{ animationDelay: "0.6s" }} />
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider opacity-90">
              <Trophy className="h-3.5 w-3.5" /> Level {level}
              <span className="mx-1 opacity-50">•</span>
              <Flame className="h-3.5 w-3.5" /> On a streak
            </div>
            <h1 className="mt-1 font-display text-4xl font-extrabold">Shop</h1>
            <p className="mt-1 text-sm opacity-85">Spend the points you've earned.</p>
          </div>
          <div className="animate-badge-bounce rounded-2xl bg-background/15 px-4 py-3 text-right backdrop-blur">
            <div className="text-[10px] font-bold uppercase tracking-wider opacity-80">Your points</div>
            <div className="flex items-center gap-1.5 font-display text-3xl font-extrabold">
              <Gem className="h-6 w-6" /> {points.toLocaleString()}
            </div>
          </div>
        </div>
        {nextReward && (
          <div className="mt-5">
            <div className="mb-1.5 flex items-center justify-between text-xs opacity-90">
              <span>Next up: {nextReward.name}</span>
              <span>{points} / {nextReward.reward_cost} pts</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-background/20">
              <div
                className="h-full rounded-full bg-primary-foreground/90 transition-all duration-700"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {rewards.map((r: any) => {
          const affordable = points >= r.reward_cost;
          const pct = Math.min(100, Math.round((points / r.reward_cost) * 100));
          return (
            <div
              key={r.id || r.reward_id || r.name}
              className={`duo-card group relative overflow-hidden p-5 transition ${
                affordable ? "border-primary/50 shadow-glow hover:-translate-y-0.5" : ""
              }`}
            >
              {affordable && <Sparkles className="animate-sparkle absolute right-3 top-3 h-4 w-4 text-primary" />}
              <div className="flex items-center justify-between">
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-primary text-primary-foreground shadow-glow">
                  <Gift className="h-5 w-5" />
                </span>
                <span className="text-xs font-bold uppercase text-muted-foreground">
                  {(r.reward_type || "").replaceAll("_", " ")}
                </span>
              </div>
              <div className="mt-4 font-display text-lg font-bold">{r.name}</div>
              {r.reward_amount ? (
                <div className="text-sm text-muted-foreground">Value: {r.reward_amount}</div>
              ) : null}
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                <div className="h-full rounded-full bg-gradient-primary transition-all" style={{ width: `${pct}%` }} />
              </div>
              <div className="mt-4 flex items-center justify-between">
                <span className="inline-flex items-center gap-1 text-sm font-extrabold text-primary">
                  <Gem className="h-3.5 w-3.5" /> {r.reward_cost}
                </span>
                <button className="duo-btn" onClick={() => buy(r)} disabled={!affordable}>
                  {affordable ? "Redeem" : `${r.reward_cost - points} to go`}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </AppShell>
  );
}