import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Shield, Sparkles, HeartHandshake } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "YTG — Build the habit of walking away" },
      {
        name: "description",
        content:
          "YTG is a gentle, gamified companion that helps young people and adults recognize harmful content and choose to step back — reinforced with rewards, not punishment.",
      },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Link to="/" className="flex items-center gap-2 font-display text-xl font-semibold">
          <Shield className="h-5 w-5 text-primary" /> YTG
        </Link>
        <nav className="flex items-center gap-2">
          <Link to="/auth">
            <Button variant="ghost">Sign in</Button>
          </Link>
          <Link to="/auth">
            <Button>Get started</Button>
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-4xl px-6 pt-16 pb-24 text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
          <Sparkles className="h-3 w-3" /> Your Truest Guardian
        </span>
        <h1 className="mt-6 font-display text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
          Build the habit of walking away from what hurts.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          Hate and harmful ideology take root through quiet, repeated exposure. YTG watches gently,
          nudges kindly, and rewards the choice to step back — because habits, not blocks, are what
          protect us.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <Link to="/auth">
            <button className="duo-btn duo-btn-lg">Create a Guardian</button>
          </Link>
          <Link to="/auth">
            <button className="duo-btn duo-btn-outline duo-btn-lg">For myself</button>
          </Link>
        </div>
      </section>

      <section className="mx-auto grid max-w-5xl gap-6 px-6 pb-24 sm:grid-cols-3">
        {[
          {
            icon: Shield,
            title: "Watches, doesn't block",
            body: "A screen companion that recognizes restricted content and nudges you to move on.",
          },
          {
            icon: HeartHandshake,
            title: "Your voice, your care",
            body: "Guardians write the warning and applause messages themselves — so it sounds like family.",
          },
          {
            icon: Sparkles,
            title: "Rewards the right choice",
            body: "Points, streaks, and a real rewards store reinforce every time you walk away.",
          },
        ].map((f) => (
          <div key={f.title} className="rounded-2xl border border-border bg-card p-6">
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
