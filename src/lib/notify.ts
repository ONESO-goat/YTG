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
  throttleMs?: number;
}) {
  if (typeof window === "undefined" || !("Notification" in window)) return;
  if (Notification.permission !== "granted") {
    console.warn("Notification skipped: permission not granted");
    return;
  }

  const throttle = opts.throttleMs ?? 10000; // 10s cooldown
  const now = Date.now();
  if (now - lastNotifiedAt < throttle) return;
  lastNotifiedAt = now;

  try {
    const iconUrl = typeof window !== "undefined" ? `${window.location.origin}/favicon.ico` : undefined;

    const n = new Notification(opts.title ?? "YTG — gentle nudge", {
      body: opts.body,
      icon: iconUrl,
      tag: "ytg-warning",
      renotify: true,  
      silent: false,
      requireInteraction: true, // Keeps it on screen until clicked or handled
    });

    n.onclick = () => {
      window.focus();
      n.close();
    };
  } catch (e) {
    console.error("OS Notification Error:", e);
  }
}


// Call this when 'harsh' mode triggers a flag
export async function forcePictureInPictureWarning(warningText: string) {
  try {
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 200;
    const ctx = canvas.getContext("2d");

    if (ctx) {
      // Draw aggressive alert UI
      ctx.fillStyle = "#dc2626"; // Bright Red
      ctx.fillRect(0, 0, 400, 200);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 20px sans-serif";
      ctx.fillText("⚠️ HARSH WARNING ⚠️", 20, 50);
      ctx.font = "14px sans-serif";
      ctx.fillText(warningText, 20, 100);
    }

    const stream = canvas.captureStream();
    const pipVideo = document.createElement("video");
    pipVideo.srcObject = stream;
    pipVideo.muted = true;
    await pipVideo.play();

    // Force PiP mode — this stays on top of ALL browser tabs & desktop apps!
    if (document.pictureInPictureEnabled) {
      await pipVideo.requestPictureInPicture();
    }
  } catch (e) {
    console.error("PiP override failed:", e);
  }
}


// In your notify helper or scan loop:
let titleInterval: any = null;

export function flashTabTitle(msg = "🚨 RETURN IMMEDIATELY!") {
  if (titleInterval) clearInterval(titleInterval);
  let isOriginal = false;
  const originalTitle = document.title;

  titleInterval = setInterval(() => {
    document.title = isOriginal ? originalTitle : msg;
    isOriginal = !isOriginal;
  }, 500);
}

export function stopFlashingTitle(originalTitle = "YTG") {
  if (titleInterval) clearInterval(titleInterval);
  document.title = originalTitle;
}