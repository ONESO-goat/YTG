import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { Lock, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorNotice, PageHeader, Spinner } from "@/components/common";
import { RequireRole } from "@/components/RequireRole";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useMe } from "@/lib/auth";
import { keys, toastError, useRestrictions, useSettings, useUpdateSettings } from "@/lib/queries";
import type { GuardianSettings, StrictnessLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authed/_shell/settings")({
  component: () => (
    <RequireRole roles={["personal", "family-owner"]}>
      <SettingsPage />
    </RequireRole>
  ),
});

const STRICTNESS: { id: StrictnessLevel; label: string; desc: string; multiplier: number }[] = [
  {
    id: "weak",
    label: "Gentle",
    desc: "Only clear, central matches are flagged.",
    multiplier: 1.2,
  },
  {
    id: "normal",
    label: "Balanced",
    desc: "Anything that clearly relates to a restriction.",
    multiplier: 1.5,
  },
  {
    id: "harsh",
    label: "Strict",
    desc: "Partial matches too, plus a pop-up warning over other apps.",
    multiplier: 2,
  },
];

function SettingsPage() {
  const me = useMe();
  const gid = me.guardian!.id;
  const settings = useSettings(gid);

  return (
    <>
      <PageHeader
        title="Settings"
        description="Choose what your Guardian watches for and how it responds."
      />
      {settings.isPending && <Spinner label="Loading settings…" />}
      {settings.isError && (
        <ErrorNotice error={settings.error} onRetry={() => settings.refetch()} />
      )}
      {settings.data && (
        <div className="grid gap-6 lg:grid-cols-2">
          <BehaviourForm gid={gid} initial={settings.data} />
          <RestrictionsEditor gid={gid} />
        </div>
      )}
    </>
  );
}

function BehaviourForm({ gid, initial }: { gid: string; initial: GuardianSettings }) {
  const [form, setForm] = useState(initial);
  const save = useUpdateSettings(gid);
  useEffect(() => setForm(initial), [initial]);

  const dirty = JSON.stringify(form) !== JSON.stringify(initial);
  const messageProblem = (m: string) =>
    m.length < 12 || m.length > 120 ? "12–120 characters" : null;
  const invalid = !!messageProblem(form.warning_message) || !!messageProblem(form.applause_message);
  const penalty = Math.round(
    form.base_points_lost * (STRICTNESS.find((s) => s.id === form.strictness)?.multiplier ?? 1.5),
  );

  return (
    <form
      className="duo-card space-y-6 p-6"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate(form);
      }}
    >
      <fieldset>
        <legend className="font-display text-lg font-extrabold">Strictness</legend>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          {STRICTNESS.map((s) => (
            <button
              type="button"
              key={s.id}
              aria-pressed={form.strictness === s.id}
              onClick={() => setForm({ ...form, strictness: s.id })}
              className={cn(
                "rounded-2xl border-2 p-3 text-left transition",
                form.strictness === s.id
                  ? "border-primary bg-primary/10"
                  : "border-border hover:border-primary/40",
              )}
            >
              <div className="text-sm font-bold">{s.label}</div>
              <div className="mt-1 text-xs text-muted-foreground">{s.desc}</div>
            </button>
          ))}
        </div>
      </fieldset>

      <div className="space-y-4">
        <h3 className="font-display text-lg font-extrabold">Messages</h3>
        {(
          [
            ["warning_message", "Warning", "Shown when something restricted is on screen."],
            ["applause_message", "Applause", "Shown after walking away from a warning."],
          ] as const
        ).map(([field, label, hint]) => (
          <div key={field}>
            <Label htmlFor={field}>{label}</Label>
            <Textarea
              id={field}
              rows={2}
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
            />
            <p
              className={cn(
                "mt-1 text-xs",
                messageProblem(form[field]) ? "text-destructive" : "text-muted-foreground",
              )}
            >
              {messageProblem(form[field]) ?? hint}
            </p>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <h3 className="font-display text-lg font-extrabold">Consequences</h3>
        <label className="flex items-center justify-between gap-4">
          <span>
            <span className="block text-sm font-bold">Lose points for ignoring a warning</span>
            <span className="text-xs text-muted-foreground">
              After 30 seconds on flagged content, then every minute it continues (up to 3 times per
              warning). Points never go below zero, and levels are never lost.
            </span>
          </span>
          <Switch
            checked={form.points_loss_enabled}
            onCheckedChange={(v) => setForm({ ...form, points_loss_enabled: v })}
          />
        </label>
        {form.points_loss_enabled && (
          <div>
            <Label htmlFor="base_points_lost">Base points lost</Label>
            <Input
              id="base_points_lost"
              type="number"
              min={0}
              max={1000}
              value={form.base_points_lost}
              onChange={(e) =>
                setForm({
                  ...form,
                  base_points_lost: Math.min(1000, Math.max(0, Number(e.target.value) || 0)),
                })
              }
            />
            <p className="mt-1 text-xs text-muted-foreground">
              At this strictness that's {penalty} points per ignored warning, doubled after 5
              warnings in a day.
            </p>
          </div>
        )}
        <label className="flex items-center justify-between gap-4">
          <span>
            <span className="block text-sm font-bold">Reports</span>
            <span className="text-xs text-muted-foreground">
              Write a short report each time something is flagged.
            </span>
          </span>
          <Switch
            checked={form.reports_enabled}
            onCheckedChange={(v) => setForm({ ...form, reports_enabled: v })}
          />
        </label>
      </div>

      <button className="duo-btn w-full" disabled={!dirty || invalid || save.isPending}>
        {save.isPending ? "Saving…" : "Save settings"}
      </button>
    </form>
  );
}

function RestrictionsEditor({ gid }: { gid: string }) {
  const qc = useQueryClient();
  const restrictions = useRestrictions(gid);
  const [value, setValue] = useState("");
  const onSuccess = (data: Awaited<ReturnType<typeof api.restrictions>>) =>
    qc.setQueryData(keys.restrictions(gid), data);

  const add = useMutation({
    mutationFn: (r: string) => api.addRestriction(gid, r),
    onSuccess: (data) => {
      onSuccess(data);
      setValue("");
    },
    onError: toastError,
  });
  const remove = useMutation({
    mutationFn: (r: string) => api.removeRestriction(gid, r),
    onSuccess,
    onError: toastError,
  });

  return (
    <div className="duo-card p-6">
      <h3 className="font-display text-lg font-extrabold">Restrictions</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        The kinds of content your Guardian nudges away from.
      </p>

      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim().length >= 2) add.mutate(value.trim());
        }}
      >
        <Input
          placeholder="Add a topic, e.g. gambling"
          maxLength={60}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <button
          className="duo-btn shrink-0"
          disabled={add.isPending || value.trim().length < 2}
          aria-label="Add restriction"
        >
          <Plus className="h-4 w-4" />
        </button>
      </form>

      {restrictions.isPending && (
        <div className="mt-4">
          <Spinner />
        </div>
      )}
      {restrictions.isError && <ErrorNotice error={restrictions.error} />}
      {restrictions.data && (
        <>
          <div className="mt-5 text-xs font-bold uppercase tracking-wide text-muted-foreground">
            Yours
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {restrictions.data.custom.length === 0 && (
              <span className="text-sm text-muted-foreground">None added yet.</span>
            )}
            {restrictions.data.custom.map((r) => (
              <span key={r} className="duo-chip border-primary/40">
                {r}
                <button
                  onClick={() => remove.mutate(r)}
                  disabled={remove.isPending}
                  aria-label={`Remove ${r}`}
                >
                  <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                </button>
              </span>
            ))}
          </div>
          <div className="mt-5 flex items-center gap-1 text-xs font-bold uppercase tracking-wide text-muted-foreground">
            <Lock className="h-3 w-3" /> Always on
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {restrictions.data.default.map((r) => (
              <span key={r} className="duo-chip text-muted-foreground">
                {r}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
