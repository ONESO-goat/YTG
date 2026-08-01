import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Users, User, Shield } from "lucide-react";
import { toast } from "sonner";
import { localSession } from "@/lib/api";

export const Route = createFileRoute("/onboarding")({
  head: () => ({ meta: [{ title: "Set up your Guardian — YTG" }] }),
  component: Onboarding,
});

function Onboarding() {
  const nav = useNavigate();
  const [type, setType] = useState<"family" | "personal">("personal");

  useEffect(() => {
    const s = localSession.get();
    if (!s) nav({ to: "/auth" });
  }, [nav]);

  function next() {
    if (type !== "personal"){
      toast.error("Family accounts are coming in the future!")
      return;
    }
    nav({ to: "/guardian/create", search: { type } });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-xl">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2 font-display text-2xl font-extrabold">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-primary text-primary-foreground shadow-glow">
            <Shield className="h-5 w-5" />
          </span>
          <span className="bg-gradient-primary bg-clip-text text-transparent">YTG</span>
        </Link>
        <div className="duo-card p-8">
          <h1 className="font-display text-3xl font-extrabold">Who is this for?</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            You can change this later. Family accounts let you connect dependents.
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {(
              [
                { id: "personal", label: "For myself", icon: User, desc: "Solo — no guardian involved." },
                { id: "family", label: `For my family (unavailable)`, icon: Users, desc: "Connect one or more dependents." },
              ] as const
            ).map((o) => (
              <button
                key={o.id}
                onClick={() => setType(o.id)}
                className={`rounded-2xl border-2 p-5 text-left transition ${
                  type === o.id
                    ? "border-primary bg-primary/10 shadow-glow"
                    : "border-border bg-card hover:border-primary/40"
                }`}
              >
                <o.icon className="h-6 w-6 text-primary" />
                <div className="mt-3 font-bold">{o.label}</div>
                <div className="text-xs text-muted-foreground">{o.desc}</div>
              </button>
            ))}
          </div>
          <button className="duo-btn duo-btn-lg mt-6 w-full" onClick={next}>
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
