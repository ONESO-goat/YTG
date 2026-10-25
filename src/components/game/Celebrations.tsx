import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useRefreshProgress } from "@/lib/queries";
import type { GameEvent } from "@/lib/types";
import { Confetti } from "./Confetti";
import { gameIcon } from "./icons";

const CelebrateContext = createContext<(events: GameEvent[]) => void>(() => {});

/** Shows level-ups as a full celebration and other game events as toasts. */
export function CelebrationProvider({ children }: { children: ReactNode }) {
  const [levelUps, setLevelUps] = useState<GameEvent[]>([]);
  // Key of the confetti burst on screen, if any
  const [burst, setBurst] = useState<number | null>(null);
  useEffect(() => {
    if (burst === null) return;
    const id = setTimeout(() => setBurst(null), 3500);
    return () => clearTimeout(id);
  }, [burst]);
  const refreshProgress = useRefreshProgress();

  const celebrate = useCallback(
    (events: GameEvent[]) => {
      if (!events.length) return;
      refreshProgress();
      for (const e of events) {
        if (e.type === "level_up") continue;
        const Icon = gameIcon(e.icon);
        const reward = e.points ? ` +${e.points} points` : "";
        toast(e.type === "achievement" ? `Badge unlocked: ${e.title}` : e.title, {
          description: `${e.description}${reward}`,
          icon: <Icon className="h-5 w-5 text-primary" />,
          duration: 6000,
        });
      }
      const ups = events.filter((e) => e.type === "level_up");
      if (ups.length) setLevelUps((prev) => [...prev, ...ups]);
      if (ups.length || events.some((e) => e.type === "achievement" || e.type === "goal")) {
        setBurst(Date.now());
      }
    },
    [refreshProgress],
  );

  const current = levelUps[0];

  return (
    <CelebrateContext.Provider value={celebrate}>
      {children}
      {burst !== null && <Confetti key={burst} />}
      <Dialog
        open={!!current}
        onOpenChange={(open) => !open && setLevelUps((prev) => prev.slice(1))}
      >
        <DialogContent className="max-w-sm text-center">
          <div className="mx-auto flex h-24 w-24 animate-badge-bounce items-center justify-center rounded-3xl bg-gradient-primary text-primary-foreground shadow-glow">
            <span className="font-display text-5xl font-extrabold">
              {current?.title.match(/\d+/)?.[0]}
            </span>
          </div>
          <DialogTitle className="mt-2 font-display text-3xl font-extrabold">
            {current?.title}
          </DialogTitle>
          <DialogDescription className="text-base">{current?.description}</DialogDescription>
          <button
            className="duo-btn duo-btn-lg mt-2 w-full"
            onClick={() => setLevelUps((p) => p.slice(1))}
          >
            Keep going
          </button>
        </DialogContent>
      </Dialog>
    </CelebrateContext.Provider>
  );
}

export const useCelebrate = () => useContext(CelebrateContext);
