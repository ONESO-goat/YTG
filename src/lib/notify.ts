// OS-level notifications that show even when the browser tab isn't focused.
// Requires HTTPS (or localhost) and a one-time user permission grant.
export async function ensureNotificationPermission(): Promise<boolean> {
  if (typeof window === "undefined" || !("Notification" in window)) return false;
  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;
  const result = await Notification.requestPermission();
  return result === "granted";
}
let lastNotifiedAt = 0;
export function sendWarningNotification(opts: {
  title?: string;
  body: string;
  // Throttle so we don't spam if the loop keeps flagging the same thing.
  throttleMs?: number;
}) {
  if (typeof window === "undefined" || !("Notification" in window)) return;
  if (Notification.permission !== "granted") return;
  const throttle = opts.throttleMs ?? 15000;
  const now = Date.now();
  if (now - lastNotifiedAt < throttle) return;
  lastNotifiedAt = now;
  try {
    const n = new Notification(opts.title ?? "YTG — gentle nudge", {
      body: opts.body,
      icon: "/favicon.ico",
      badge: "/favicon.ico",
      tag: "ytg-warning", // replaces any previous unread YTG warning
      requireInteraction: false,
    });
    // Focus the tab if the user clicks the OS notification.
    n.onclick = () => {
      window.focus();
      n.close();
    };
  } catch {
    // Some browsers require ServiceWorkerRegistration.showNotification instead;
    // silently ignore — the in-app banner still shows.
  }
}
