import { formatDistanceToNowStrict } from "date-fns";

/** The backend stores naive UTC timestamps, so mark them as UTC before parsing. */
export function parseServerDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(value);
  const date = new Date(hasZone || value.length <= 10 ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function timeAgo(value: string | null | undefined): string {
  const date = parseServerDate(value);
  return date ? `${formatDistanceToNowStrict(date)} ago` : "never";
}

/** A monitored session that scanned recently is considered live. */
export function isLive(active: boolean, lastScanAt: string | null): boolean {
  const last = parseServerDate(lastScanAt);
  return active && !!last && Date.now() - last.getTime() < 30_000;
}
