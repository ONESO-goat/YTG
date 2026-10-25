import { useMutation } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useAuth, useMe } from "@/lib/auth";
import { toastError } from "@/lib/queries";

export const Route = createFileRoute("/_authed/_shell/account")({
  component: Account,
});

const ACCOUNT_LABELS = {
  individual: "Personal",
  caregiver: "Family guardian",
  dependent: "Family member",
};

function Account() {
  const me = useMe();
  const { refresh, logout } = useAuth();
  const [name, setName] = useState(me.user.name);
  const [pw, setPw] = useState({ current: "", next: "" });

  const rename = useMutation({
    mutationFn: () => api.updateName(name.trim()),
    onSuccess: () => {
      toast.success("Name updated");
      refresh();
    },
    onError: toastError,
  });
  const changePassword = useMutation({
    mutationFn: () => api.changePassword(pw.current, pw.next),
    onSuccess: () => {
      toast.success("Password changed");
      setPw({ current: "", next: "" });
    },
    onError: toastError,
  });

  return (
    <>
      <PageHeader title="Account" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="duo-card space-y-3 p-6 text-sm">
          <h3 className="font-display text-lg font-extrabold">Profile</h3>
          <Row label="Username" value={`@${me.user.username}`} />
          <Row label="Email" value={me.user.email} />
          <Row label="Account type" value={ACCOUNT_LABELS[me.user.user_type]} />
          <Row label="Your ID" value={<span className="font-mono">{me.user.number_id}</span>} />
          {me.guardian && <Row label="Guardian" value={me.guardian.name} />}
          <form
            className="space-y-2 pt-3"
            onSubmit={(e) => {
              e.preventDefault();
              rename.mutate();
            }}
          >
            <Label htmlFor="name">Display name</Label>
            <div className="flex gap-2">
              <Input
                id="name"
                minLength={3}
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <button
                className="duo-btn shrink-0"
                disabled={
                  rename.isPending || name.trim().length < 3 || name.trim() === me.user.name
                }
              >
                Save
              </button>
            </div>
          </form>
        </div>

        <form
          className="duo-card space-y-4 p-6"
          onSubmit={(e) => {
            e.preventDefault();
            changePassword.mutate();
          }}
        >
          <h3 className="font-display text-lg font-extrabold">Change password</h3>
          <div>
            <Label htmlFor="pw-current">Current password</Label>
            <Input
              id="pw-current"
              type="password"
              autoComplete="current-password"
              required
              value={pw.current}
              onChange={(e) => setPw({ ...pw, current: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="pw-next">New password</Label>
            <Input
              id="pw-next"
              type="password"
              autoComplete="new-password"
              required
              value={pw.next}
              onChange={(e) => setPw({ ...pw, next: e.target.value })}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              10+ characters with an uppercase letter and a number.
            </p>
          </div>
          <button className="duo-btn w-full" disabled={changePassword.isPending}>
            Update password
          </button>
        </form>
      </div>
      <button className="duo-btn duo-btn-outline mt-6" onClick={logout}>
        Sign out
      </button>
    </>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="truncate font-bold">{value}</span>
    </div>
  );
}
