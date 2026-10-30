import { createFileRoute, Link } from "@tanstack/react-router";
import { Gift, HeartHandshake, Shield, Sparkles } from "lucide-react";
import { Logo } from "@/components/common";
import { Knight } from "@/components/game/Knight";
import { homePath, useAuth } from "@/lib/auth";

export const Route = createFileRoute("/")({
  component: Landing,
});

const FEATURES = [
  {
    icon: Shield,
    title: "Watches, doesn't block",
    body: "Your knight spots restricted content and nudges you to move on.",
  },
  {
    icon: HeartHandshake,
    title: "Your voice",
    body: "Guardians write the warning and cheer messages, so it sounds like family.",
  },
  {
    icon: Sparkles,
    title: "Earn XP",
    body: "Clean minutes and heeded warnings level you up and grow your streak.",
  },
  {
    icon: Gift,
    title: "Spend it",
    body: "Trade points for gift cards and streak freezes in the shop.",
  },
];

function Landing() {
  const { me } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Logo />
        <nav className="flex items-center gap-3">
          {me ? (
            <Link to={homePath(me)} className="btn">
              Open YTG
            </Link>
          ) : (
            <>
              <Link
                to="/auth"
                search={{ mode: "login" }}
                className="px-2 text-sm font-semibold text-muted-foreground hover:text-foreground"
              >
                Sign in
              </Link>
              <Link to="/auth" search={{ mode: "signup" }} className="btn">
                Get started
              </Link>
            </>
          )}
        </nav>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 pt-10 pb-20 md:grid-cols-[1fr_auto]">
        <div>
          <span className="chip text-xs text-primary">Your truest guardian</span>
          <h1 className="mt-6 text-2xl leading-[1.6] sm:text-3xl sm:leading-[1.5]">
            Build the habit of walking away from what hurts.
          </h1>
          <p className="mt-6 max-w-xl text-lg text-muted-foreground">
            Hate and harmful ideology take root through quiet, repeated exposure. Your knight
            watches gently, nudges kindly, and rewards the choice to step back.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link to="/auth" search={{ mode: "signup", type: "individual" }} className="btn btn-lg">
              Start for myself
            </Link>
            <Link
              to="/auth"
              search={{ mode: "signup", type: "caregiver" }}
              className="btn btn-outline btn-lg"
            >
              Guard my family
            </Link>
          </div>
        </div>
        <div className="flex justify-center md:justify-end">
          <div className="panel flex flex-col items-center px-10 pt-10 pb-6">
            <Knight scale={4} animate />
            <p className="mt-5 font-display text-xs text-primary">Ready when you are</p>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-6 pb-24 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f) => (
          <div key={f.title} className="panel p-6">
            <f.icon className="h-6 w-6 text-primary" />
            <h3 className="mt-4 text-xs leading-relaxed">{f.title}</h3>
            <p className="mt-3 text-sm text-muted-foreground">{f.body}</p>
          </div>
        ))}
      </section>

      <footer className="border-t-2 border-border py-8 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} YTG · Built with care
      </footer>
    </div>
  );
}
