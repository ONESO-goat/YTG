import { useQueryClient } from "@tanstack/react-query";
import { Navigate, createFileRoute } from "@tanstack/react-router";
import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";
import { Logo } from "@/components/common";
import { homePath, meQueryKey, useAuth, useMe } from "@/lib/auth";

export const Route = createFileRoute("/_authed/waiting")({
  component: Waiting,
});

function Waiting() {
  const me = useMe();
  const { logout } = useAuth();
  const qc = useQueryClient();
  const [copied, setCopied] = useState(false);

  // Check every few seconds whether a guardian has connected this account
  useEffect(() => {
    const id = setInterval(() => qc.invalidateQueries({ queryKey: meQueryKey }), 3000);
    return () => clearInterval(id);
  }, [qc]);

  if (homePath(me) !== "/waiting") return <Navigate to={homePath(me)} />;

  const numberId = String(me.user.number_id);
  async function copy() {
    try {
      await navigator.clipboard.writeText(numberId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked: the ID is still visible to read out */
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md text-center">
        <Logo className="mb-6 justify-center" />
        <div className="duo-card space-y-6 p-8">
          <div className="relative mx-auto flex h-24 w-24 items-center justify-center">
            <span className="absolute h-24 w-24 animate-ping rounded-full bg-primary/20" />
            <span className="relative h-14 w-14 rounded-2xl bg-gradient-primary shadow-glow" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-extrabold">Waiting for your guardian</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Give this ID to your parent or guardian. They add it from their YTG dashboard.
            </p>
          </div>
          <div className="rounded-2xl border-2 border-primary/30 bg-primary/5 p-4">
            <div className="text-xs font-bold uppercase tracking-widest text-primary">Your ID</div>
            <div className="mt-1 font-mono text-4xl font-black tracking-wider">{numberId}</div>
            <button className="duo-btn mt-4 w-full" onClick={copy}>
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? "Copied" : "Copy ID"}
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            This page moves on by itself once you're connected.
          </p>
          <button className="text-xs text-muted-foreground underline" onClick={logout}>
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
