import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { Gem, Gift, Package, Snowflake } from "lucide-react";
import { toast } from "sonner";
import { EmptyState, ErrorNotice, PageHeader, Spinner, formatPoints } from "@/components/common";
import { useCelebrate } from "@/components/game/Celebrations";
import { RequireRole } from "@/components/RequireRole";
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
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { parseServerDate } from "@/lib/format";
import {
  keys,
  toastError,
  useMyRewards,
  useProgress,
  useRefreshProgress,
  useRewards,
} from "@/lib/queries";
import type { OwnedReward, PurchaseResult, Reward, Streak } from "@/lib/types";

export const Route = createFileRoute("/_authed/_shell/shop")({
  component: () => (
    <RequireRole roles={["personal", "member"]}>
      <Shop />
    </RequireRole>
  ),
});

// Roughly what a day of good habits earns: the clean-minute cap plus a goal and a few bonuses
const POINTS_PER_GOOD_DAY = 700;
// Matches REFUND_RATE in services/gameify_service.py
const REFUND_RATE = 5 / 6;

function Shop() {
  const me = useMe();
  const rewards = useRewards();
  const owned = useMyRewards();
  const progress = useProgress();

  return (
    <>
      <PageHeader
        title="Shop"
        description="Trade the points you earn for real rewards."
        action={
          <div className="chip text-base">
            <Gem className="h-5 w-5 text-primary" /> {formatPoints(me.user.currency)}
          </div>
        }
      />

      {rewards.isPending && <Spinner label="Loading rewards…" />}
      {rewards.isError && <ErrorNotice error={rewards.error} onRetry={() => rewards.refetch()} />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {rewards.data?.map((r) => (
          <RewardCard
            key={r.id}
            reward={r}
            balance={me.user.currency}
            streak={progress.data?.streak}
          />
        ))}
      </div>

      <section className="mt-10">
        <h2 className="mb-3 font-display text-base">Your rewards</h2>
        {owned.isPending && <Spinner />}
        {owned.isError && <ErrorNotice error={owned.error} onRetry={() => owned.refetch()} />}
        {owned.data?.length === 0 && (
          <EmptyState icon={Package} title="Nothing here yet">
            Gift cards you buy show up here. Streak freezes go straight to your streak.
          </EmptyState>
        )}
        <ul className="space-y-2">
          {owned.data?.map((o) => (
            <li key={o.id} className="panel flex items-center justify-between gap-3 p-4">
              <span className="flex items-center gap-3">
                <RewardIcon reward={o.reward} />
                <span>
                  <span className="block font-bold">{o.reward.name}</span>
                  <span className="text-xs text-muted-foreground">
                    Order #{o.order_id}
                    {o.purchased_at &&
                      ` · bought ${parseServerDate(o.purchased_at)?.toLocaleDateString()}`}
                  </span>
                </span>
              </span>
              <RefundButton owned={o} />
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

function RewardIcon({ reward }: { reward: Reward }) {
  const Icon = reward.type === "streak_freeze" ? Snowflake : Gift;
  return (
    <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/10 text-primary">
      <Icon className="h-5 w-5" />
    </span>
  );
}

function useShopMutation(fn: () => Promise<PurchaseResult>, success: string) {
  const qc = useQueryClient();
  const celebrate = useCelebrate();
  const refreshProgress = useRefreshProgress();
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      toast.success(success);
      refreshProgress();
      qc.invalidateQueries({ queryKey: keys.myRewards });
      celebrate(result.events);
    },
    onError: toastError,
  });
}

function RewardCard({
  reward,
  balance,
  streak,
}: {
  reward: Reward;
  balance: number;
  streak?: Streak;
}) {
  const buy = useShopMutation(() => api.buyReward(reward.id), `You got ${reward.name}`);
  const isFreeze = reward.type === "streak_freeze";
  const freezesFull = isFreeze && !!streak && streak.freezes >= streak.max_freezes;
  const affordable = balance >= reward.cost;
  const missing = reward.cost - balance;
  const days = Math.ceil(missing / POINTS_PER_GOOD_DAY);

  return (
    <div className="panel flex flex-col p-5">
      <RewardIcon reward={reward} />
      <div className="mt-3 flex-1 font-bold">{reward.name}</div>
      {isFreeze && (
        <p className="mt-1 text-xs text-muted-foreground">
          Protects your streak on a day you miss your goal.
          {streak && ` You have ${streak.freezes} of ${streak.max_freezes}.`}
        </p>
      )}
      <div className="mt-2 flex items-center gap-1 font-display text-base">
        <Gem className="h-4 w-4 text-primary" /> {formatPoints(reward.cost)}
      </div>
      <Progress className="mt-3" value={Math.min(100, (balance / reward.cost) * 100)} />
      <div className="mt-1 text-xs text-muted-foreground">
        {freezesFull
          ? "You're holding the most freezes you can."
          : affordable
            ? "You can afford this!"
            : `${formatPoints(missing)} to go (about ${days} good day${days === 1 ? "" : "s"})`}
      </div>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <button className="btn mt-4" disabled={!affordable || freezesFull || buy.isPending}>
            {buy.isPending ? "Buying…" : "Buy"}
          </button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Buy {reward.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              {formatPoints(reward.cost)} points will leave your balance.{" "}
              {isFreeze
                ? "Streak freezes can't be refunded."
                : "You can refund it within 24 hours for most of the cost back."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Not now</AlertDialogCancel>
            <AlertDialogAction onClick={() => buy.mutate()}>Buy it</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function RefundButton({ owned }: { owned: OwnedReward }) {
  const refund = useShopMutation(() => api.refundReward(owned.id), "Refunded");
  const until = parseServerDate(owned.refundable_until);
  if (!until || until.getTime() < Date.now()) {
    return <span className="text-xs text-muted-foreground">Final sale</span>;
  }
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <button
          className="text-xs font-bold text-muted-foreground underline"
          disabled={refund.isPending}
        >
          Refund
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Refund {owned.reward.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            You'll get {formatPoints(Math.floor(owned.reward.cost * REFUND_RATE))} points back.
            Refunds are possible until {until.toLocaleString()}.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep it</AlertDialogCancel>
          <AlertDialogAction onClick={() => refund.mutate()}>Refund</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
