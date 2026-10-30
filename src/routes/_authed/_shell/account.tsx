import { useMutation } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common";
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
  const { refresh, logout, adoptToken } = useAuth();
  const [name, setName] = useState(me.user.name);
  const [pw, setPw] = useState({ current: "", next: "" });
  const [deletePassword, setDeletePassword] = useState("");

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
    onSuccess: (r) => {
      adoptToken(r.access_token);
      toast.success("Password changed. Other devices have been signed out.");
      setPw({ current: "", next: "" });
    },
    onError: toastError,
  });
  const deleteAccount = useMutation({
    mutationFn: () => api.deleteAccount(deletePassword),
    onSuccess: () => {
      toast.success("Your account has been deleted");
      logout();
    },
    onError: toastError,
  });

  return (
    <>
      <PageHeader title="Account" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="panel space-y-3 p-6 text-sm">
          <h3 className="font-display text-sm">Profile</h3>
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
                className="btn shrink-0"
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
          className="panel space-y-4 p-6"
          onSubmit={(e) => {
            e.preventDefault();
            changePassword.mutate();
          }}
        >
          <h3 className="font-display text-sm">Change password</h3>
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
          <button className="btn w-full" disabled={changePassword.isPending}>
            Update password
          </button>
        </form>
      </div>
      <button className="btn btn-outline mt-6" onClick={logout}>
        Sign out
      </button>

      <section className="mt-10 rounded-2xl border-2 border-destructive/30 p-6">
        <h3 className="font-display text-sm text-destructive">Delete account</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {me.is_guardian_owner && me.guardian?.guardian_type === "family"
            ? "This also deletes your family guardian. Its members are disconnected and their reports removed."
            : "Your points, badges and history are deleted for good."}
        </p>
        <AlertDialog onOpenChange={(open) => !open && setDeletePassword("")}>
          <AlertDialogTrigger asChild>
            <button className="mt-4 text-sm font-bold text-destructive underline">
              Delete my account
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete your account?</AlertDialogTitle>
              <AlertDialogDescription>
                This can't be undone. Enter your password to confirm.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <Input
              type="password"
              autoComplete="current-password"
              aria-label="Password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
            />
            <AlertDialogFooter>
              <AlertDialogCancel>Keep my account</AlertDialogCancel>
              <AlertDialogAction
                disabled={!deletePassword || deleteAccount.isPending}
                onClick={(e) => {
                  e.preventDefault();
                  deleteAccount.mutate();
                }}
              >
                Delete forever
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </section>
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
