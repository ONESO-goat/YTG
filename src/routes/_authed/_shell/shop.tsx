import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { Gem, Gift, Package, Snowflake } from "lucide-react";
import { toast } from "sonner";
import { EmptyState, ErrorNotice, PageHeader, Spinner, formatPoints } from "@/components/common";
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
import { meQueryKey, useMe } from "@/lib/auth";
import { keys, toastError, useMyRewards, useRewards } from "@/lib/queries";
import type { Reward } from "@/lib/types";

export const Route = createFileRoute("/_authed/_shell/shop")({
  component: () => (
    <RequireRole roles={["personal", "member"]}>
      <Shop />
    </RequireRole>
  ),
});

// Matches the points the backend hands out for a clean minute
const POINTS_PER_CLEAN_MINUTE = 10;

function Shop() {
  const me = useMe();
  const rewards = useRewards();
  const owned = useMyRewards();

  return (
    <>
      <PageHeader
        title="Shop"
        description="Trade the points you earn for real rewards."
        action={
          <div className="duo-chip text-base">
            <Gem className="h-5 w-5 text-primary" /> {formatPoints(me.user.currency)}
          </div>
        }
      />

      {rewards.isPending && <Spinner label="Loading rewards…" />}
      {rewards.isError && <ErrorNotice error={rewards.error} onRetry={() => rewards.refetch()} />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {rewards.data?.map((r) => (
          <RewardCard key={r.id} reward={r} balance={me.user.currency} />
        ))}
      </div>

      <section className="mt-10">
        <h2 className="mb-3 font-display text-xl font-extrabold">Your rewards</h2>
        {owned.isPending && <Spinner />}
        {owned.isError && <ErrorNotice error={owned.error} onRetry={() => owned.refetch()} />}
        {owned.data?.length === 0 && (
          <EmptyState icon={Package} title="Nothing here yet">
            Rewards you buy show up here.
          </EmptyState>
        )}
        <ul className="space-y-2">
          {owned.data?.map((o) => (
            <li key={o.id} className="duo-card flex items-center justify-between gap-3 p-4">
              <span className="flex items-center gap-3">
                <RewardIcon reward={o.reward} />
                <span>
                  <span className="block font-bold">{o.reward.name}</span>
                  <span className="text-xs text-muted-foreground">Order #{o.order_id}</span>
                </span>
              </span>
              <RefundButton reward={o.reward} />
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

function useBalanceMutation(
  fn: () => Promise<{ message: string; currency: number }>,
  success: string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      toast.success(success);
      qc.invalidateQueries({ queryKey: meQueryKey });
      qc.invalidateQueries({ queryKey: keys.myRewards });
    },
    onError: toastError,
  });
}

function RewardCard({ reward, balance }: { reward: Reward; balance: number }) {
  const buy = useBalanceMutation(() => api.buyReward(reward.id), `You got ${reward.name}`);
  const affordable = balance >= reward.cost;
  const missing = reward.cost - balance;
  const minutesLeft = Math.ceil(missing / POINTS_PER_CLEAN_MINUTE);

  return (
    <div className="duo-card flex flex-col p-5">
      <RewardIcon reward={reward} />
      <div className="mt-3 flex-1 font-bold">{reward.name}</div>
      <div className="mt-2 flex items-center gap-1 font-display text-xl font-extrabold">
        <Gem className="h-4 w-4 text-primary" /> {formatPoints(reward.cost)}
      </div>
      <Progress className="mt-3" value={Math.min(100, (balance / reward.cost) * 100)} />
      <div className="mt-1 text-xs text-muted-foreground">
        {affordable
          ? "You can afford this!"
          : `${formatPoints(missing)} to go (about ${minutesLeft >= 60 ? `${Math.ceil(minutesLeft / 60)} h` : `${minutesLeft} min`} of clean browsing)`}
      </div>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <button className="duo-btn mt-4" disabled={!affordable || buy.isPending}>
            {buy.isPending ? "Buying…" : "Buy"}
          </button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Buy {reward.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              {formatPoints(reward.cost)} points will leave your balance. Refunds return about 83%
              of the cost.
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

function RefundButton({ reward }: { reward: Reward }) {
  const refund = useBalanceMutation(() => api.refundReward(reward.id), "Refunded");
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
          <AlertDialogTitle>Refund {reward.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            You'll get {formatPoints(Math.floor(reward.cost / 1.2))} points back.
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
