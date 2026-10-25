import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import {
  Ban,
  Flame,
  Gem,
  HeartHandshake,
  PlayCircle,
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
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { isLive, timeAgo } from "@/lib/format";
import { keys, toastError, useMembers, useMySession, useToggleGuardian } from "@/lib/queries";
import { roleOf } from "@/lib/roles";
import type { Guardian, MemberOverview, UserSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authed/_shell/dashboard")({
  component: Dashboard,
});

const DAILY_LIMIT = 10_000;

function Dashboard() {
  const me = useMe();
  return roleOf(me) === "family-owner" ? <FamilyDashboard /> : <PersonalDashboard />;
}

function MonitoringSwitch({ guardian }: { guardian: Guardian }) {
  const toggle = useToggleGuardian(guardian.id);
  return (
    <label className="duo-card flex cursor-pointer items-center gap-3 px-4 py-3">
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
  const s = session.data;
  const dailyLeft = s?.points_gain_daily_limit ?? DAILY_LIMIT;

  return (
    <>
      <PageHeader
        title={`Hi, ${me.user.name}!`}
        description={isMember ? `Guarded by ${guardian.name}` : guardian.name}
        action={!isMember && <MonitoringSwitch guardian={guardian} />}
      />

      <div className="duo-card mb-6 flex flex-col items-start justify-between gap-4 bg-gradient-primary p-6 text-primary-foreground sm:flex-row sm:items-center">
        <div>
          <div className="font-display text-2xl font-extrabold">
            {guardian.on ? "Ready for a session?" : "Monitoring is paused"}
          </div>
          <p className="mt-1 text-sm opacity-90">
            {guardian.on
              ? "Every clean minute earns points. Walk away from a warning and earn a bonus."
              : isMember
                ? "Your guardian has paused monitoring for now."
                : "Turn monitoring on to start earning points."}
          </p>
        </div>
        {guardian.on && (
          <Link to="/monitor" className="duo-btn duo-btn-outline duo-btn-lg">
            <PlayCircle className="h-5 w-5" /> {s?.active ? "Open session" : "Start session"}
          </Link>
        )}
      </div>

      {session.isError && <ErrorNotice error={session.error} onRetry={() => session.refetch()} />}

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard
          icon={Gem}
          label="Points"
          value={formatPoints(me.user.currency)}
          hint={
            <Link to="/shop" className="underline">
              Visit the shop
            </Link>
          }
        />
        <StatCard
          icon={Flame}
          label="Streak"
          value={`${s?.streak ?? 0} ${s?.streak === 1 ? "day" : "days"}`}
          tone="warm"
          hint="Come back each day to grow it"
        />
        <StatCard
          icon={HeartHandshake}
          label="Warnings heeded"
          value={s?.amount_of_warnings_listened ?? 0}
          tone="success"
          hint="Today"
        />
        <StatCard
          icon={Ban}
          label="Warnings ignored"
          value={s?.amount_of_warnings_ignored ?? 0}
          tone="destructive"
          hint="Today"
        />
      </div>

      <div className="duo-card mt-4 p-5">
        <div className="flex items-center justify-between text-sm">
          <span className="font-bold">Points you can still earn today</span>
          <span className="text-muted-foreground">
            {formatPoints(Math.max(dailyLeft, 0))} / {formatPoints(DAILY_LIMIT)}
          </span>
        </div>
        <Progress className="mt-3" value={(Math.max(dailyLeft, 0) / DAILY_LIMIT) * 100} />
      </div>

      {!isMember && (
        <section className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-display text-xl font-extrabold">Recent reports</h2>
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
        <h2 className="mb-3 font-display text-xl font-extrabold">Members</h2>
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

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-xl font-extrabold">Recent reports</h2>
          <Link to="/reports" className="text-sm font-bold text-primary">
            See all
          </Link>
        </div>
        <ReportList guardianId={guardian.id} limit={5} />
      </section>
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
    <div className="duo-card p-5">
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
        <button className="duo-btn shrink-0" disabled={!raw || lookup.isPending || add.isPending}>
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
  const { user, session } = member;
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
    <div className="duo-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 font-display text-lg font-extrabold text-primary">
            {user.name.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <div className="font-bold">{user.name}</div>
            <div className="text-xs text-muted-foreground">@{user.username}</div>
          </div>
        </div>
        <span
          className={cn(
            "duo-chip text-xs",
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

      <dl className="mt-4 grid grid-cols-4 gap-2 text-center">
        {[
          ["Points", formatPoints(user.currency)],
          ["Streak", session?.streak ?? 0],
          ["Heeded", session?.amount_of_warnings_listened ?? 0],
          ["Ignored", session?.amount_of_warnings_ignored ?? 0],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl bg-muted p-2">
            <dt className="text-[10px] font-bold uppercase text-muted-foreground">{label}</dt>
            <dd className="font-display text-lg font-extrabold">{value}</dd>
          </div>
        ))}
      </dl>

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
