import { createFileRoute, Link } from "@tanstack/react-router";
import { Gift, HeartHandshake, Shield, Sparkles } from "lucide-react";
import { Logo } from "@/components/common";
import { homePath, useAuth } from "@/lib/auth";

export const Route = createFileRoute("/")({
  component: Landing,
});

function Landing() {
  const { me } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Logo className="text-xl" />
        <nav className="flex items-center gap-2">
          {me ? (
            <Link to={homePath(me)} className="duo-btn">
              Open YTG
            </Link>
          ) : (
            <>
              <Link
                to="/auth"
                search={{ mode: "login" }}
                className="px-3 text-sm font-bold text-muted-foreground hover:text-foreground"
              >
                Sign in
              </Link>
              <Link to="/auth" search={{ mode: "signup" }} className="duo-btn">
                Get started
              </Link>
            </>
          )}
        </nav>
      </header>

      <section className="mx-auto max-w-4xl px-6 pt-16 pb-24 text-center">
        <h1 className="mt-6 font-display text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
          Build the habit of walking away from what hurts.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          Hate and harmful ideology take root through quiet, repeated exposure. YTG watches gently,
          nudges kindly, and rewards the choice to step back, because habits, not blocks, are what
          protect us.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <Link
            to="/auth"
            search={{ mode: "signup", type: "individual" }}
            className="duo-btn duo-btn-lg"
          >
            Start for myself
          </Link>
          <Link
            to="/auth"
            search={{ mode: "signup", type: "caregiver" }}
            className="duo-btn duo-btn-outline duo-btn-lg"
          >
            Guard my family
          </Link>
        </div>
      </section>

      <section className="mx-auto grid max-w-5xl gap-6 px-6 pb-24 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            icon: Shield,
            title: "Watches, doesn't block",
            body: "A screen companion that recognizes restricted content and nudges you to move on.",
          },
          {
            icon: HeartHandshake,
            title: "Your voice, your care",
            body: "Guardians write the warning and applause messages themselves, so it sounds like family.",
          },
          {
            icon: Sparkles,
            title: "Rewards the right choice",
            body: "Every minute of clean browsing and every warning you heed earns points.",
          },
          {
            icon: Gift,
            title: "Spend what you earn",
            body: "Trade points for gift cards and streak freezes in the shop.",
          },
        ].map((f) => (
          <div key={f.title} className="duo-card p-6">
            <f.icon className="h-5 w-5 text-primary" />
            <h3 className="mt-3 text-lg font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{f.body}</p>
          </div>
        ))}
      </section>

      <footer className="border-t border-border py-8 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} YTG · Built with care
      </footer>
    </div>
  );
}
