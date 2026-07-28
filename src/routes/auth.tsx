import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Shield } from "lucide-react";
import { api, localSession, pickId } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — YTG" },
      { name: "description", content: "Sign in or create your YTG account." },
    ],
  }),
  component: AuthPage,
});

async function routeAfterAuth(nav: ReturnType<typeof useNavigate>, user_id: string) {
  // Try to find an existing guardian for this user. If found → dashboard.
  try {
    const g: any = await api.getGuardianByOwner(user_id);
    const gid = pickId(g, "guardian_id", "id");
    if (gid) {
      localSession.patch({ role: "guardian", guardian_id: gid });
      nav({ to: "/guardian/dashboard" });
      return;
    }
  } catch {
    /* no guardian yet — fall through */
  }
  nav({ to: "/onboarding" });
}

function AuthPage() {
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [login, setLogin] = useState({ username: "", password: "" });
  const [signup, setSignup] = useState({ username: "", email: "", password: "" });

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    // Always start clean — no stale IDs from previous sessions.
    localSession.clear();
    try {
      const r: any = await api.login(login);
      const uid = pickId(r, "user_id", "id");
      if (!uid) throw new Error("No user_id returned from backend");
      localSession.set({ user_id: uid, username: login.username, role: "individual" });
      toast.success("Welcome back");
      await routeAfterAuth(nav, uid);
    } catch (err: any) {
      toast.error(err?.message || "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    localSession.clear();
    try {
      const r: any = await api.signup(signup);
      const uid = pickId(r, "user_id", "id");
      if (!uid) throw new Error("No user_id returned from backend");
      localSession.set({ user_id: uid, username: signup.username, role: "individual" });
      toast.success("Welcome to YTG");
      nav({ to: "/onboarding" });
    } catch (err: any) {
      toast.error(err?.message || "Sign up failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2 font-display text-2xl font-extrabold">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-primary text-primary-foreground shadow-glow">
            <Shield className="h-5 w-5" />
          </span>
          <span className="bg-gradient-primary bg-clip-text text-transparent">YTG</span>
        </Link>
        <div className="duo-card p-6">
          <Tabs defaultValue="signup">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="signup">Create account</TabsTrigger>
              <TabsTrigger value="login">Sign in</TabsTrigger>
            </TabsList>
            <TabsContent value="signup">
              <form onSubmit={handleSignup} className="mt-4 space-y-4">
                <div>
                  <Label htmlFor="s-user">Username</Label>
                  <Input id="s-user" required value={signup.username} onChange={(e) => setSignup({ ...signup, username: e.target.value })} />
                </div>
                <div>
                  <Label htmlFor="s-email">Email</Label>
                  <Input id="s-email" type="email" required value={signup.email} onChange={(e) => setSignup({ ...signup, email: e.target.value })} />
                </div>
                <div>
                  <Label htmlFor="s-pw">Password</Label>
                  <Input id="s-pw" type="password" required value={signup.password} onChange={(e) => setSignup({ ...signup, password: e.target.value })} />
                </div>
                <button type="submit" className="duo-btn duo-btn-lg w-full" disabled={busy}>
                  {busy ? "Creating..." : "Create account"}
                </button>
              </form>
            </TabsContent>
            <TabsContent value="login">
              <form onSubmit={handleLogin} className="mt-4 space-y-4">
                <div>
                  <Label htmlFor="l-user">Username</Label>
                  <Input id="l-user" required value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })} />
                </div>
                <div>
                  <Label htmlFor="l-pw">Password</Label>
                  <Input id="l-pw" type="password" required value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} />
                </div>
                <button type="submit" className="duo-btn duo-btn-lg w-full" disabled={busy}>
                  {busy ? "Signing in..." : "Sign in"}
                </button>
              </form>
            </TabsContent>
          </Tabs>
        </div>
        <p className="mt-4 text-center text-xs text-muted-foreground">
          Trouble signing in? Clear this device{" "}
          <button
            className="underline"
            onClick={() => {
              localSession.clear();
              toast.success("Local session cleared");
            }}
          >
            here
          </button>
          .
        </p>
      </div>
    </div>
  );
}
