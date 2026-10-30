import { cn } from "@/lib/utils";

export type KnightMood = "calm" | "alert" | "happy" | "sleepy";

const MOODS: KnightMood[] = ["calm", "alert", "happy", "sleepy"];
// Native sprite sizes in public/knight, so scaling stays a whole multiple of each pixel
const NATIVE = { full: { w: 64, h: 73 }, head: { w: 26, h: 31 } };

// Load every mood up front so switching moods never flashes an empty frame
if (typeof window !== "undefined") {
  for (const mood of MOODS) {
    for (const prefix of ["", "head-"]) new Image().src = `/knight/${prefix}${mood}.png`;
  }
}

/** The YTG guardian: a purple pixel knight whose eyes show how things are going. */
export function Knight({
  mood = "calm",
  variant = "full",
  scale = 2,
  animate = false,
  className,
}: {
  mood?: KnightMood;
  variant?: "full" | "head";
  /** Whole-number multiple of the native sprite size */
  scale?: number;
  animate?: boolean;
  className?: string;
}) {
  const { w, h } = NATIVE[variant];
  return (
    <img
      src={`/knight/${variant === "head" ? "head-" : ""}${mood}.png`}
      width={w * scale}
      height={h * scale}
      alt=""
      aria-hidden
      draggable={false}
      className={cn(
        "pixelated select-none",
        animate && (mood === "alert" ? "animate-knight-alert" : "animate-knight"),
        className,
      )}
    />
  );
}
