import { Lock, Snowflake, Flame, Crown, Medal } from "lucide-react";
import { formatPoints } from "@/components/common";
import { Progress as Bar } from "@/components/ui/progress";
import type { Achievement, LeaderboardEntry, Progress, Streak } from "@/lib/types";
import { cn } from "@/lib/utils";
import { gameIcon } from "./icons";

export function LevelCard({ progress }: { progress: Progress }) {
  const pct = (progress.xp_into_level / progress.xp_for_next_level) * 100;
  return (
    <div className="panel flex items-center gap-4 p-5">
      <div className="flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-2xl bg-primary text-primary-foreground">
        <span className="text-[10px] font-bold uppercase opacity-80">Level</span>
        <span className="font-display text-lg leading-none">{progress.level}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-display text-base">{progress.title}</div>
        <Bar className="mt-2 h-3" value={pct} aria-label="XP toward next level" />
        <div className="mt-1 text-xs text-muted-foreground">
          {formatPoints(progress.xp_into_level)} / {formatPoints(progress.xp_for_next_level)} XP to
          level {progress.level + 1}
        </div>
      </div>
    </div>
  );
}

export function StreakCard({ streak }: { streak: Streak }) {
  const lit = streak.current > 0;
  return (
    <div className="panel p-5">
      <div className="flex items-center gap-4">
        <div
          className={cn(
            "flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl",
            lit ? "bg-warm/40 text-orange-500" : "bg-muted text-muted-foreground",
          )}
        >
          <Flame className={cn("h-9 w-9", lit && streak.done_today && "animate-soft-pulse")} />
        </div>
        <div>
          <div className="font-display text-lg">
            {streak.current} day{streak.current === 1 ? "" : "s"}
          </div>
          <div className="text-xs text-muted-foreground">Best: {streak.best}</div>
        </div>
      </div>
      <div className="mt-3 text-sm">
        {streak.done_today ? (
          <span className="font-bold text-success">Today's goal is done. See you tomorrow!</span>
        ) : streak.at_risk ? (
          <span className="font-bold text-warm-foreground">
            Finish today's goal to keep your streak.
          </span>
        ) : (
          <span className="text-muted-foreground">Complete today's goal to start a streak.</span>
        )}
      </div>
      <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
        {Array.from({ length: streak.max_freezes }, (_, i) => (
          <Snowflake
            key={i}
            className={cn("h-4 w-4", i < streak.freezes ? "text-sky-500" : "opacity-30")}
          />
        ))}
        <span>
          {streak.freezes} of {streak.max_freezes} streak freezes
        </span>
      </div>
    </div>
  );
}

/** A ring that fills up with today's clean minutes. */
export function GoalRing({
  value,
  goal,
  size = 120,
  label = "min",
}: {
  value: number;
  goal: number;
  size?: number;
  label?: string;
}) {
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.min(value / goal, 1);
  const done = pct >= 1;
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          className="stroke-border"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          className={cn("transition-all duration-700", done ? "stroke-success" : "stroke-primary")}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-lg">{Math.min(value, goal)}</span>
        <span className="text-[11px] text-muted-foreground">
          / {goal} {label}
        </span>
      </div>
    </div>
  );
}

export function AchievementTile({ achievement: a }: { achievement: Achievement }) {
  const Icon = gameIcon(a.icon);
  const unlocked = !!a.unlocked_at;
  return (
    <div
      className={cn(
        "panel flex flex-col items-center p-4 text-center transition",
        !unlocked && "opacity-80",
      )}
    >
      <div
        className={cn(
          "relative flex h-14 w-14 items-center justify-center rounded-2xl",
          unlocked ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
        )}
      >
        <Icon className="h-7 w-7" />
        {!unlocked && (
          <span className="absolute -bottom-1 -right-1 rounded-full bg-card p-0.5">
            <Lock className="h-3.5 w-3.5" />
          </span>
        )}
      </div>
      <div className="mt-3 text-sm font-bold">{a.name}</div>
      <div className="mt-1 text-xs text-muted-foreground">{a.description}</div>
      {unlocked ? (
        <div className="mt-2 text-xs font-bold text-success">+{a.points} earned</div>
      ) : (
        <div className="mt-2 w-full">
          <Bar className="h-1.5" value={(a.progress / a.target) * 100} />
          <div className="mt-1 text-[11px] text-muted-foreground">
            {a.progress} / {a.target} · +{a.points}
          </div>
        </div>
      )}
    </div>
  );
}

export function LeaderboardList({
  entries,
  me,
}: {
  entries: LeaderboardEntry[];
  me?: LeaderboardEntry | null;
}) {
  return (
    <ol className="panel divide-y-2 divide-border">
      {entries.map((e) => (
        <LeaderboardRow key={e.username} entry={e} />
      ))}
      {me && (
        <>
          <li className="px-4 py-1 text-center text-xs text-muted-foreground">···</li>
          <LeaderboardRow entry={me} />
        </>
      )}
    </ol>
  );
}

function LeaderboardRow({ entry: e }: { entry: LeaderboardEntry }) {
  const medal = ["text-amber-500", "text-slate-400", "text-orange-700"][e.rank - 1];
  return (
    <li className={cn("flex items-center gap-3 px-4 py-3", e.is_me && "bg-primary/10")}>
      <span className="flex w-7 justify-center font-display text-sm">
        {e.rank === 1 ? (
          <Crown className={cn("h-5 w-5", medal)} />
        ) : medal ? (
          <Medal className={cn("h-5 w-5", medal)} />
        ) : e.rank > 0 ? (
          e.rank
        ) : (
          "–"
        )}
      </span>
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 font-bold text-primary">
        {e.name.slice(0, 1).toUpperCase()}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-bold">
          {e.name} {e.is_me && <span className="text-xs font-normal text-primary">(you)</span>}
        </span>
        <span className="text-xs text-muted-foreground">
          Level {e.level}
          {e.streak > 0 && (
            <>
              {" · "}
              <Flame className="inline h-3 w-3 text-orange-500" /> {e.streak}
            </>
          )}
        </span>
      </span>
      <span className="text-right">
        <span className="block font-display text-sm">{formatPoints(e.weekly_xp)}</span>
        <span className="text-[11px] text-muted-foreground">XP this week</span>
      </span>
    </li>
  );
}
