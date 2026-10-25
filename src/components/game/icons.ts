import {
  Award,
  CalendarCheck,
  Crown,
  Flame,
  Footprints,
  Gift,
  HeartHandshake,
  Leaf,
  Repeat,
  Rocket,
  Shield,
  ShieldCheck,
  Snowflake,
  Sparkles,
  Star,
  Sun,
  Target,
  Trophy,
  type LucideIcon,
} from "lucide-react";

// Icon names the backend sends with achievements and game events
const ICONS: Record<string, LucideIcon> = {
  "calendar-check": CalendarCheck,
  crown: Crown,
  flame: Flame,
  footprints: Footprints,
  gift: Gift,
  "heart-handshake": HeartHandshake,
  leaf: Leaf,
  repeat: Repeat,
  rocket: Rocket,
  shield: Shield,
  "shield-check": ShieldCheck,
  snowflake: Snowflake,
  sparkles: Sparkles,
  star: Star,
  sun: Sun,
  target: Target,
  trophy: Trophy,
};

export const gameIcon = (name: string): LucideIcon => ICONS[name] ?? Award;
