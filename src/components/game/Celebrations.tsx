import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useRefreshProgress } from "@/lib/queries";
import type { GameEvent } from "@/lib/types";
import { Confetti } from "./Confetti";
import { Knight } from "./Knight";
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
          <div className="relative mx-auto">
            <Knight mood="happy" scale={2} animate />
            <span className="absolute -right-6 bottom-2 animate-badge-bounce rounded-md bg-gold px-2 py-1.5 font-display text-sm text-primary-foreground">
              {current?.title.match(/\d+/)?.[0]}
            </span>
          </div>
          <DialogTitle className="mt-2 font-display text-xl">{current?.title}</DialogTitle>
          <DialogDescription className="text-base">{current?.description}</DialogDescription>
          <button className="btn btn-lg mt-2 w-full" onClick={() => setLevelUps((p) => p.slice(1))}>
            Keep going
          </button>
        </DialogContent>
      </Dialog>
    </CelebrateContext.Provider>
  );
}

export const useCelebrate = () => useContext(CelebrateContext);
