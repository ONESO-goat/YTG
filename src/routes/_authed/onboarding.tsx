import { Navigate, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Logo } from "@/components/common";
import { Knight } from "@/components/game/Knight";
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
  const [name, setName] = useState(isFamily ? `The ${me.user.name} family` : "Sir Violet");
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

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-lg">
        <Logo className="mb-6 justify-center" />
        <form className="panel p-8" onSubmit={create}>
          <Knight mood="happy" scale={2} animate className="mx-auto" />
          <h1 className="mt-6 text-center font-display text-lg">Name your knight</h1>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            {isFamily
              ? "Your knight watches over your family. Next, connect your kids with the ID shown on their screen."
              : "Your knight nudges you away from content you want to avoid, and rewards you when you do."}
          </p>
          <div className="mt-6">
            <Label htmlFor="gname">Knight name</Label>
            <Input
              id="gname"
              required
              maxLength={120}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <button className="btn btn-lg mt-6 w-full" disabled={busy || !name.trim()}>
            {busy ? "Summoning…" : "Summon my knight"}
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
