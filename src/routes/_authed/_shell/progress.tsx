import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Trophy } from "lucide-react";
import { z } from "zod";
import { EmptyState, ErrorNotice, PageHeader, Spinner } from "@/components/common";
import { AchievementTile, LeaderboardList, LevelCard } from "@/components/game/widgets";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { keys, toastError, useAchievements, useLeaderboard, useProgress } from "@/lib/queries";
import { roleOf } from "@/lib/roles";

const searchSchema = z.object({
  tab: z.enum(["badges", "leaderboard"]).catch("badges").optional(),
});

export const Route = createFileRoute("/_authed/_shell/progress")({
  validateSearch: searchSchema,
  component: ProgressPage,
});

function ProgressPage() {
  const me = useMe();
  const role = roleOf(me);
  const nav = useNavigate({ from: Route.fullPath });
  const { tab } = Route.useSearch();

  // Guardian owners don't earn anything themselves; they only follow their family's board
  if (role === "family-owner") {
    return (
      <>
        <PageHeader title="Family leaderboard" description="Who earned the most XP this week." />
        <Board scope="family" />
      </>
    );
  }

  return (
    <>
      <PageHeader title="Progress" description="Levels, badges and how you compare this week." />
      <Tabs
        value={tab ?? "badges"}
        onValueChange={(v) => nav({ search: { tab: v as "badges" | "leaderboard" } })}
      >
        <TabsList className="mb-6">
          <TabsTrigger value="badges">Badges</TabsTrigger>
          <TabsTrigger value="leaderboard">Leaderboard</TabsTrigger>
        </TabsList>
        <TabsContent value="badges">
          <Badges />
        </TabsContent>
        <TabsContent value="leaderboard">
          {role === "member" ? (
            <Board scope="family" />
          ) : (
            <>
              <LeaderboardOptIn />
              <Board scope="global" />
            </>
          )}
        </TabsContent>
      </Tabs>
    </>
  );
}

function Badges() {
  const progress = useProgress();
  const achievements = useAchievements();
  if (achievements.isPending) return <Spinner label="Loading badges…" />;
  if (achievements.isError)
    return <ErrorNotice error={achievements.error} onRetry={() => achievements.refetch()} />;

  const unlocked = achievements.data.filter((a) => a.unlocked_at);
  const locked = achievements.data.filter((a) => !a.unlocked_at);
  return (
    <div className="space-y-8">
      {progress.data && <LevelCard progress={progress.data} />}
      <section>
        <h2 className="mb-3 font-display text-base">
          Unlocked{" "}
          <span className="text-sm font-normal text-muted-foreground">
            {unlocked.length}/{achievements.data.length}
          </span>
        </h2>
        {unlocked.length ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {unlocked.map((a) => (
              <AchievementTile key={a.code} achievement={a} />
            ))}
          </div>
        ) : (
          <EmptyState icon={Trophy} title="No badges yet">
            Start a session to unlock your first one.
          </EmptyState>
        )}
      </section>
      {locked.length > 0 && (
        <section>
          <h2 className="mb-3 font-display text-base">Still to earn</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {locked.map((a) => (
              <AchievementTile key={a.code} achievement={a} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Board({ scope }: { scope: "family" | "global" }) {
  const board = useLeaderboard(scope);
  if (board.isPending) return <Spinner label="Loading leaderboard…" />;
  if (board.isError) return <ErrorNotice error={board.error} onRetry={() => board.refetch()} />;
  if (!board.data.entries.length && !board.data.me) {
    return (
      <EmptyState icon={Trophy} title="Nobody here yet">
        {scope === "family"
          ? "Once your family starts sessions, their weekly XP shows up here."
          : "Be the first to join the leaderboard."}
      </EmptyState>
    );
  }
  return (
    <>
      <LeaderboardList
        entries={board.data.entries}
        me={board.data.visible ? board.data.me : null}
      />
      <p className="mt-3 text-center text-xs text-muted-foreground">
        Ranked by XP earned over the last 7 days. Levels never go down, but this board resets as the
        week moves on.
      </p>
    </>
  );
}

function LeaderboardOptIn() {
  const qc = useQueryClient();
  const progress = useProgress();
  const toggle = useMutation({
    mutationFn: (show: boolean) => api.updatePreferences({ show_on_leaderboard: show }),
    onSuccess: (p) => {
      qc.setQueryData(keys.progress, p);
      qc.invalidateQueries({ queryKey: ["progress", "leaderboard"] });
    },
    onError: toastError,
  });
  if (!progress.data) return null;
  return (
    <label className="panel mb-4 flex cursor-pointer items-center justify-between gap-4 p-4">
      <span>
        <span className="block text-sm font-bold">Show me on the leaderboard</span>
        <span className="text-xs text-muted-foreground">
          Others will see your display name, level and weekly XP. Nothing else.
        </span>
      </span>
      <Switch
        checked={progress.data.show_on_leaderboard}
        disabled={toggle.isPending}
        onCheckedChange={(v) => toggle.mutate(v)}
      />
    </label>
  );
}
