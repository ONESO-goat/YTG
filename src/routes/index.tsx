import { createFileRoute } from "@tanstack/react-router";
import { Compass, Shield, Sparkles, Trophy, ArrowRight } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Guardian's Compass — Your Truest Guardian" },
      {
        name: "description",
        content:
          "A mindful companion that intercepts harmful online habits and rewards kinder choices with real perks.",
      },
      { property: "og:title", content: "Guardian's Compass" },
      {
        property: "og:description",
        content:
          "A mindful companion that intercepts harmful online habits and rewards kinder choices with real perks.",
      },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <Compass className="h-6 w-6 text-primary" />
          <span className="font-semibold tracking-tight">Guardian's Compass</span>
        </div>
        <a
          href="#get-started"
          className="inline-flex items-center gap-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Get started <ArrowRight className="h-4 w-4" />
        </a>
      </header>

      <main>
        <section className="mx-auto max-w-4xl px-6 pb-20 pt-16 text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" /> Kinder scrolling, rewarded
          </div>
          <h1 className="text-balance text-5xl font-semibold tracking-tight sm:text-6xl">
            Your truest guardian, quietly on your side.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg text-muted-foreground">
            Guardian's Compass gently interrupts harmful patterns online — and pays you back
            in points when you choose the kinder path.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <a
              id="get-started"
              href="#features"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Explore how it works <ArrowRight className="h-4 w-4" />
            </a>
            <a
              href="#why"
              className="inline-flex items-center rounded-md border border-input bg-background px-5 py-3 text-sm font-medium transition-colors hover:bg-accent"
            >
              Why it matters
            </a>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-6xl px-6 pb-24">
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              {
                icon: Shield,
                title: "Private by design",
                body: "No hoarding, no selling. The compass only watches for harm — never you.",
              },
              {
                icon: Compass,
                title: "Nudges, not walls",
                body: "A soft prompt when a moment turns sharp. You still choose — but with clarity.",
              },
              {
                icon: Trophy,
                title: "Real rewards",
                body: "Earn points for kinder choices. Redeem for gift cards, passes, and perks.",
              },
            ].map(({ icon: Icon, title, body }) => (
              <div
                key={title}
                className="rounded-xl border border-border bg-card p-6 shadow-sm"
              >
                <Icon className="mb-4 h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="why" className="mx-auto max-w-4xl px-6 pb-28">
          <div className="rounded-2xl border border-border bg-muted/30 p-8 sm:p-12">
            <h2 className="text-3xl font-semibold tracking-tight">Why we built this</h2>
            <p className="mt-4 text-muted-foreground">
              Social media has become the hub where inequality is taught and reinforced. We
              can't end it, but we can quiet it — especially for the young people who spend
              the most time inside it. Guardian's Compass is a small, respectful voice that
              helps steer the moment.
            </p>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6 text-sm text-muted-foreground">
          <span>© {new Date().getFullYear()} Guardian's Compass</span>
          <span>Built with care.</span>
        </div>
      </footer>
    </div>
  );
}
