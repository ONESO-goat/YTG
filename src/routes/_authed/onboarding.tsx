import { Navigate, createFileRoute, useNavigate } from "@tanstack/react-router";
import { Users, User } from "lucide-react";
import { useState } from "react";
import { Logo } from "@/components/common";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { homePath, useAuth, useMe } from "@/lib/auth";
import { toastError } from "@/lib/queries";

export const Route = createFileRoute("/_authed/onboarding")({
  component: Onboarding,
});

function Onboarding() {
  const me = useMe();
  const { refresh, logout } = useAuth();
  const nav = useNavigate();
  const isFamily = me.user.user_type === "caregiver";
  const [name, setName] = useState(
    isFamily ? `The ${me.user.name} family` : `${me.user.name}'s guardian`,
  );
  const [busy, setBusy] = useState(false);

  if (homePath(me) !== "/onboarding") return <Navigate to={homePath(me)} />;

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.createGuardian(name);
      await refresh();
      nav({ to: "/dashboard" });
    } catch (err) {
      toastError(err);
    } finally {
      setBusy(false);
    }
  }

  const Icon = isFamily ? Users : User;
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-lg">
        <Logo className="mb-6 justify-center" />
        <form className="duo-card p-8" onSubmit={create}>
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Icon className="h-6 w-6" />
          </span>
          <h1 className="mt-4 font-display text-3xl font-extrabold">Name your Guardian</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {isFamily
              ? "Your Guardian watches over your family. Next you'll connect your kids with the ID shown on their screen."
              : "Your Guardian is the companion that nudges you away from content you want to avoid, and rewards you when you do."}
          </p>
          <div className="mt-6">
            <Label htmlFor="gname">Guardian name</Label>
            <Input
              id="gname"
              required
              maxLength={120}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <button className="duo-btn duo-btn-lg mt-6 w-full" disabled={busy || !name.trim()}>
            {busy ? "Creating…" : "Create Guardian"}
          </button>
          <button
            type="button"
            className="mt-4 w-full text-xs text-muted-foreground underline"
            onClick={logout}
          >
            Sign out
          </button>
        </form>
      </div>
    </div>
  );
}
