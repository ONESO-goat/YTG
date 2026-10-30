import { Navigate, createFileRoute, useNavigate } from "@tanstack/react-router";
import { Baby, User, Users, type LucideIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { FullPageSpinner, Logo } from "@/components/common";
import { Knight } from "@/components/game/Knight";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { homePath, useAuth } from "@/lib/auth";
import type { UserType } from "@/lib/types";
import { cn } from "@/lib/utils";

const searchSchema = z.object({
  mode: z.enum(["login", "signup"]).catch("signup").optional(),
  type: z.enum(["individual", "caregiver", "dependent"]).catch("individual").optional(),
});

export const Route = createFileRoute("/auth")({
  validateSearch: searchSchema,
  component: AuthPage,
});

const ACCOUNT_TYPES: { id: UserType; label: string; desc: string; icon: LucideIcon }[] = [
  { id: "individual", label: "Just me", desc: "Build better habits for yourself.", icon: User },
  {
    id: "caregiver",
    label: "My family",
    desc: "Guard your kids and see their progress.",
    icon: Users,
  },
  {
    id: "dependent",
    label: "I was invited",
    desc: "A parent or guardian will connect you.",
    icon: Baby,
  },
];

function passwordProblem(pw: string): string | null {
  if (pw.length < 10) return "At least 10 characters";
  if (!/[A-Z]/.test(pw) || !/\d/.test(pw)) return "Needs an uppercase letter and a number";
  return null;
}

function AuthPage() {
  const nav = useNavigate();
  const search = Route.useSearch();
  const { status, me, login, signup } = useAuth();
  const [busy, setBusy] = useState(false);
  const [loginForm, setLoginForm] = useState({ identifier: "", password: "" });
  const [signupForm, setSignupForm] = useState({
    username: "",
    email: "",
    password: "",
    user_type: (search.type ?? "individual") as UserType,
  });

  if (status === "loading") return <FullPageSpinner />;
  if (status === "authenticated" && me && !busy) return <Navigate to={homePath(me)} />;

  async function run(action: () => Promise<Parameters<typeof homePath>[0]>, welcome: string) {
    setBusy(true);
    try {
      const result = await action();
      toast.success(welcome);
      nav({ to: homePath(result) });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const pwProblem = signupForm.password ? passwordProblem(signupForm.password) : null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md">
        <Knight scale={2} animate className="mx-auto mb-4" />
        <Logo className="mb-6 justify-center" />
        <div className="panel p-6">
          <Tabs defaultValue={search.mode ?? "signup"}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="signup">Create account</TabsTrigger>
              <TabsTrigger value="login">Sign in</TabsTrigger>
            </TabsList>

            <TabsContent value="signup">
              <form
                className="mt-4 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (pwProblem) return toast.error(pwProblem);
                  run(() => signup(signupForm), "Welcome to YTG!");
                }}
              >
                <fieldset>
                  <legend className="mb-2 text-sm font-medium">Who is this account for?</legend>
                  <div className="grid gap-2 sm:grid-cols-3">
                    {ACCOUNT_TYPES.map((t) => (
                      <button
                        type="button"
                        key={t.id}
                        onClick={() => setSignupForm({ ...signupForm, user_type: t.id })}
                        aria-pressed={signupForm.user_type === t.id}
                        className={cn(
                          "rounded-2xl border-2 p-3 text-left transition",
                          signupForm.user_type === t.id
                            ? "border-primary bg-primary/10"
                            : "border-border bg-card hover:border-primary/40",
                        )}
                      >
                        <t.icon className="h-5 w-5 text-primary" />
                        <div className="mt-2 text-sm font-bold">{t.label}</div>
                        <div className="text-xs text-muted-foreground">{t.desc}</div>
                      </button>
                    ))}
                  </div>
                </fieldset>
                <div>
                  <Label htmlFor="s-user">Username</Label>
                  <Input
                    id="s-user"
                    required
                    minLength={3}
                    autoComplete="username"
                    value={signupForm.username}
                    onChange={(e) => setSignupForm({ ...signupForm, username: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="s-email">Email</Label>
                  <Input
                    id="s-email"
                    type="email"
                    required
                    autoComplete="email"
                    value={signupForm.email}
                    onChange={(e) => setSignupForm({ ...signupForm, email: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="s-pw">Password</Label>
                  <Input
                    id="s-pw"
                    type="password"
                    required
                    autoComplete="new-password"
                    value={signupForm.password}
                    onChange={(e) => setSignupForm({ ...signupForm, password: e.target.value })}
                  />
                  <p
                    className={cn(
                      "mt-1 text-xs",
                      pwProblem ? "text-destructive" : "text-muted-foreground",
                    )}
                  >
                    {pwProblem ?? "10+ characters with an uppercase letter and a number."}
                  </p>
                </div>
                <button type="submit" className="btn btn-lg w-full" disabled={busy}>
                  {busy ? "Creating…" : "Create account"}
                </button>
              </form>
            </TabsContent>

            <TabsContent value="login">
              <form
                className="mt-4 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(() => login(loginForm.identifier, loginForm.password), "Welcome back!");
                }}
              >
                <div>
                  <Label htmlFor="l-user">Username or email</Label>
                  <Input
                    id="l-user"
                    required
                    autoComplete="username"
                    value={loginForm.identifier}
                    onChange={(e) => setLoginForm({ ...loginForm, identifier: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="l-pw">Password</Label>
                  <Input
                    id="l-pw"
                    type="password"
                    required
                    autoComplete="current-password"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                  />
                </div>
                <button type="submit" className="btn btn-lg w-full" disabled={busy}>
                  {busy ? "Signing in…" : "Sign in"}
                </button>
              </form>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
