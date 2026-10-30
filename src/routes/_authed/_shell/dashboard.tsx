import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import {
  Ban,
  Gem,
  HeartHandshake,
  PlayCircle,
  Sparkles,
  Trophy,
  ShieldCheck,
  ShieldOff,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  EmptyState,
  ErrorNotice,
  PageHeader,
  Spinner,
  StatCard,
  formatPoints,
} from "@/components/common";
import { ReportList } from "@/components/ReportList";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Knight, type KnightMood } from "@/components/game/Knight";
import {
  AchievementTile,
  GoalRing,
  LeaderboardList,
  LevelCard,
  StreakCard,
} from "@/components/game/widgets";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { isLive, timeAgo } from "@/lib/format";
import {
  keys,
  toastError,
  useAchievements,
  useLeaderboard,
  useMembers,
  useMySession,
  useProgress,
  useToggleGuardian,
} from "@/lib/queries";
import { roleOf } from "@/lib/roles";
import type { Guardian, MemberOverview, UserSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authed/_shell/dashboard")({
  component: Dashboard,
});

function Dashboard() {
  const me = useMe();
  return roleOf(me) === "family-owner" ? <FamilyDashboard /> : <PersonalDashboard />;
}

function MonitoringSwitch({ guardian }: { guardian: Guardian }) {
  const toggle = useToggleGuardian(guardian.id);
  return (
    <label className="panel flex cursor-pointer items-center gap-3 px-4 py-3">
      {guardian.on ? (
        <ShieldCheck className="h-5 w-5 text-success" />
      ) : (
        <ShieldOff className="h-5 w-5 text-muted-foreground" />
      )}
      <div>
        <div className="text-sm font-bold">Monitoring {guardian.on ? "on" : "paused"}</div>
        <div className="text-xs text-muted-foreground">
          {guardian.on ? "Sessions can run" : "No sessions can start"}
        </div>
      </div>
      <Switch
        checked={guardian.on}
        disabled={toggle.isPending}
        onCheckedChange={(on) => toggle.mutate(on)}
      />
    </label>
  );
}

function PersonalDashboard() {
  const me = useMe();
  const guardian = me.guardian!;
  const isMember = roleOf(me) === "member";
  const session = useMySession();
  const progress = useProgress();
  const p = progress.data;
  const heroMood: KnightMood = !guardian.on ? "sleepy" : p?.today.goal_completed ? "happy" : "calm";

  return (
    <>
      <PageHeader
        title={`Hi, ${me.user.name}!`}
        description={isMember ? `Guarded by ${guardian.name}` : guardian.name}
        action={!isMember && <MonitoringSwitch guardian={guardian} />}
      />

      <div className="panel mb-4 grid items-center gap-6 p-6 md:grid-cols-[auto_1fr_auto]">
        <div className="flex justify-center">
          <Knight scale={2} animate mood={heroMood} />
        </div>
        <div>
          <div className="font-display text-[10px] text-primary">Today's quest</div>
          <div className="mt-3 font-display text-base leading-relaxed">
            {!guardian.on
              ? "Monitoring is paused"
              : p?.today.goal_completed
                ? "Quest complete!"
                : `Browse ${p?.today.goal_minutes ?? 15} clean minutes`}
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {!guardian.on
              ? isMember
                ? "Your guardian has paused monitoring for now."
                : "Turn monitoring on to start earning."
              : p?.today.goal_completed
                ? "Everything else today is a bonus. Your knight is proud of you."
                : "Every clean minute earns points. Walk away from a warning for a bonus."}
          </p>
          {p && (
            <div className="mt-4 max-w-sm">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Minute points today</span>
                <span>
                  {p.today.minute_points} / {p.today.minute_points_cap}
                </span>
              </div>
              <Progress
                className="mt-1.5 h-2"
                value={(p.today.minute_points / p.today.minute_points_cap) * 100}
              />
            </div>
          )}
          {guardian.on && (
            <Link to="/monitor" className="btn btn-lg mt-6">
              <PlayCircle className="h-4 w-4" />
              {session.data?.active ? "Open session" : "Start session"}
            </Link>
          )}
        </div>
        {p && (
          <div className="flex justify-center">
            <GoalRing value={p.today.clean_minutes} goal={p.today.goal_minutes} size={140} />
          </div>
        )}
      </div>

      {progress.isPending && <Spinner label="Loading your progress…" />}
      {progress.isError && (
        <ErrorNotice error={progress.error} onRetry={() => progress.refetch()} />
      )}
      {p && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <LevelCard progress={p} />
            <StreakCard streak={p.streak} />
          </div>

          <h2 className="mb-3 mt-8 font-display text-base">Today</h2>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            <StatCard
              icon={Gem}
              label="Points"
              value={formatPoints(me.user.currency)}
              hint={
                <span>
                  <span className="text-success">+{p.today.points_earned}</span>
                  {p.today.points_lost > 0 && (
                    <span className="text-destructive"> / -{p.today.points_lost}</span>
                  )}{" "}
                  today
                </span>
              }
            />
            <StatCard
              icon={Sparkles}
              label="XP today"
              value={`+${formatPoints(p.today.xp_earned)}`}
              hint={`${formatPoints(p.xp)} XP all time`}
            />
            <StatCard
              icon={HeartHandshake}
              label="Heeded"
              value={p.today.warnings_heeded}
              tone="success"
              hint={`${p.today.avoidance_bonuses_left} bonuses left today`}
            />
            <StatCard
              icon={Ban}
              label="Ignored"
              value={p.today.warnings_ignored}
              tone="destructive"
              hint={
                p.today.warnings_ignored ? "Ignoring warnings costs points" : "Keep it at zero!"
              }
            />
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            <BadgesPreview />
            <LeaderboardPreview scope={isMember ? "family" : "global"} />
          </div>
        </>
      )}

      {!isMember && (
        <section className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-base">Recent reports</h2>
            <Link to="/reports" className="text-sm font-bold text-primary">
              See all
            </Link>
          </div>
          <ReportList guardianId={guardian.id} limit={3} />
        </section>
      )}
    </>
  );
}

function BadgesPreview() {
  const achievements = useAchievements();
  if (!achievements.data) return null;
  const unlocked = achievements.data.filter((a) => a.unlocked_at).length;
  // The locked badges the user is closest to
  const next = achievements.data
    .filter((a) => !a.unlocked_at)
    .sort((a, b) => b.progress / b.target - a.progress / a.target)
    .slice(0, 3);
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-base">
          Badges{" "}
          <span className="text-sm font-normal text-muted-foreground">
            {unlocked}/{achievements.data.length}
          </span>
        </h2>
        <Link to="/progress" className="text-sm font-bold text-primary">
          See all
        </Link>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {next.map((a) => (
          <AchievementTile key={a.code} achievement={a} />
        ))}
      </div>
    </section>
  );
}

function LeaderboardPreview({ scope }: { scope: "family" | "global" }) {
  const board = useLeaderboard(scope);
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-base">
          {scope === "family" ? "Family leaderboard" : "Leaderboard"}
        </h2>
        <Link
          to="/progress"
          search={{ tab: "leaderboard" }}
          className="text-sm font-bold text-primary"
        >
          See all
        </Link>
      </div>
      {board.data && (board.data.visible || scope === "family") ? (
        <LeaderboardList
          entries={board.data.entries.slice(0, 5)}
          me={board.data.visible ? board.data.me : null}
        />
      ) : (
        <EmptyState icon={Trophy} title="Join the leaderboard">
          Compare your weekly XP with others. You can opt in on the{" "}
          <Link
            to="/progress"
            search={{ tab: "leaderboard" }}
            className="font-bold text-primary underline"
          >
            Progress page
          </Link>
          .
        </EmptyState>
      )}
    </section>
  );
}

function FamilyDashboard() {
  const me = useMe();
  const guardian = me.guardian!;
  const members = useMembers(guardian.id);

  return (
    <>
      <PageHeader
        title={guardian.name}
        description="Your family at a glance"
        action={<MonitoringSwitch guardian={guardian} />}
      />

      <AddMember guardianId={guardian.id} />

      <section className="mt-6">
        <h2 className="mb-3 font-display text-base">Members</h2>
        {members.isPending && <Spinner label="Loading members…" />}
        {members.isError && <ErrorNotice error={members.error} onRetry={() => members.refetch()} />}
        {members.data?.length === 0 && (
          <EmptyState icon={Users} title="No one connected yet">
            Ask your child to create an account and choose “I was invited”. Their screen will show
            an ID to enter above.
          </EmptyState>
        )}
        <div className="grid gap-4 md:grid-cols-2">
          {members.data?.map((m) => (
            <MemberCard key={m.connection.id} guardianId={guardian.id} member={m} />
          ))}
        </div>
      </section>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        {!!members.data?.length && <LeaderboardPreview scope="family" />}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-base">Recent reports</h2>
            <Link to="/reports" className="text-sm font-bold text-primary">
              See all
            </Link>
          </div>
          <ReportList guardianId={guardian.id} limit={5} />
        </section>
      </div>
    </>
  );
}

function AddMember({ guardianId }: { guardianId: string }) {
  const qc = useQueryClient();
  const [raw, setRaw] = useState("");
  const [found, setFound] = useState<UserSummary | null>(null);

  const lookup = useMutation({
    mutationFn: () => api.lookupDependent(Number(raw)),
    onSuccess: setFound,
    onError: (e) => {
      setFound(null);
      toastError(e);
    },
  });
  const add = useMutation({
    mutationFn: () => api.addMember(guardianId, Number(raw)),
    onSuccess: () => {
      toast.success(`${found?.name ?? "Member"} is connected`);
      setRaw("");
      setFound(null);
      qc.invalidateQueries({ queryKey: keys.members(guardianId) });
      qc.invalidateQueries({ queryKey: keys.reports(guardianId) });
    },
    onError: toastError,
  });

  return (
    <div className="panel p-5">
      <div className="flex items-center gap-2 font-bold">
        <UserPlus className="h-5 w-5 text-primary" /> Connect a child
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        Enter the ID shown on their “waiting for your guardian” screen.
      </p>
      <form
        className="mt-4 flex flex-col gap-2 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          if (found) add.mutate();
          else lookup.mutate();
        }}
      >
        <Input
          inputMode="numeric"
          placeholder="e.g. 4821930576"
          value={raw}
          onChange={(e) => {
            if (/^\d*$/.test(e.target.value)) {
              setRaw(e.target.value);
              setFound(null);
            }
          }}
          aria-label="Child's ID"
        />
        <button className="btn shrink-0" disabled={!raw || lookup.isPending || add.isPending}>
          {found ? `Connect ${found.name}` : lookup.isPending ? "Looking up…" : "Find"}
        </button>
      </form>
      {found && (
        <p className="mt-2 text-sm">
          Found <b>{found.name}</b> (@{found.username}). Press connect to add them.
        </p>
      )}
    </div>
  );
}

function MemberCard({ guardianId, member }: { guardianId: string; member: MemberOverview }) {
  const qc = useQueryClient();
  const { user, session, progress } = member;
  const live = session ? isLive(session.active, session.last_scan_at) : false;
  const warning = live && session?.warning_active;
  const remove = useMutation({
    mutationFn: () => api.removeMember(guardianId, user.id),
    onSuccess: (r) => {
      toast.success(r.message);
      qc.invalidateQueries({ queryKey: keys.members(guardianId) });
    },
    onError: toastError,
  });

  return (
    <div className="panel p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 font-display text-sm text-primary">
            {user.name.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <div className="font-bold">{user.name}</div>
            <div className="text-xs text-muted-foreground">@{user.username}</div>
          </div>
        </div>
        <span
          className={cn(
            "chip text-xs",
            warning
              ? "border-warm text-warm-foreground"
              : live
                ? "border-success text-success"
                : "text-muted-foreground",
          )}
        >
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              warning
                ? "bg-warm animate-soft-pulse"
                : live
                  ? "bg-success animate-soft-pulse"
                  : "bg-muted-foreground/40",
            )}
          />
          {warning ? "Warned" : live ? "Live" : "Offline"}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-4">
        <GoalRing
          value={progress.today.clean_minutes}
          goal={progress.today.goal_minutes}
          size={84}
        />
        <dl className="grid flex-1 grid-cols-2 gap-2 text-center">
          {[
            ["Level", progress.level],
            ["Streak", `${progress.streak.current} day${progress.streak.current === 1 ? "" : "s"}`],
            ["Heeded today", progress.today.warnings_heeded],
            ["Ignored today", progress.today.warnings_ignored],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl bg-muted p-2">
              <dt className="text-[10px] font-bold uppercase text-muted-foreground">{label}</dt>
              <dd className="font-display text-sm">{value}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="mt-3 text-xs text-muted-foreground">
        {formatPoints(user.currency)} points · {progress.title} ·{" "}
        {progress.today.goal_completed ? "goal done today" : "goal not done yet"}
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
        <span>Last scan {timeAgo(session?.last_scan_at)}</span>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <button className="flex items-center gap-1 rounded-lg px-2 py-1 hover:bg-muted hover:text-destructive">
              <Trash2 className="h-3.5 w-3.5" /> Remove
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remove {user.name}?</AlertDialogTitle>
              <AlertDialogDescription>
                They'll stop being monitored and go back to the waiting screen. Their points are
                kept.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={() => remove.mutate()}>Remove</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}
