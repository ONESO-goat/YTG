import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { sendWarningNotification, forcePictureInPictureWarning } from "@/lib/notify";

export function useScanLoop(
  sessionId: string | null,
  intervalMs = 5000,
  warningMessages: { warning?: string; applause?: string } = {},
  isHarsh: boolean = false,
) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<any>(null);
  const runningRef = useRef(false);
  
  // Store latest warningMessages in a ref to avoid stale closure in tick loop
  const msgsRef = useRef(warningMessages);
  useEffect(() => {
    msgsRef.current = warningMessages;
  }, [warningMessages]);

  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const [state, setState] = useState("");

  async function start(sessId: string | null = null) {
    let activeSessionId = sessId || sessionId;
   
    if (!activeSessionId) throw new Error("No sessionId provided");

    const media = await navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: 5 },
      audio: false,
    });
    streamRef.current = media;

    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.srcObject = media;
    await video.play();
    videoRef.current = video;

    canvasRef.current = document.createElement("canvas");

    media.getVideoTracks()[0].addEventListener("ended", stop);

    runningRef.current = true;
    setRunning(true);
    tick(activeSessionId);
  }

  function stop() {
    runningRef.current = false;
    setRunning(false);
    if (timerRef.current) clearTimeout(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    videoRef.current = null;
    canvasRef.current = null;
  }

  async function tick(activeSessionId: string) {
    if (!runningRef.current) return;
    try {
      await captureAndSend(activeSessionId);
    } catch (e) {
      console.error("Scan tick failed:", e);
    }
    if (runningRef.current) {
      timerRef.current = setTimeout(() => tick(activeSessionId), intervalMs);
    }
  }

  async function captureAndSend(activeSessionId: string) {
    const v = videoRef.current;
    const c = canvasRef.current;
    if (!v || !c || !activeSessionId) return;

    const w = v.videoWidth;
    const h = v.videoHeight;
    if (!w || !h) return;

    c.width = w;
    c.height = h;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(v, 0, 0, w, h);

    const blob: Blob | null = await new Promise((res) =>
      c.toBlob(res, "image/png")
    );
    if (!blob) return;

    const result = await api.scan(activeSessionId, blob);
    setLastResult(result);

    const is_flagged = result?.flagged || result?.warning_active;
    if (is_flagged) {
      const msgText = msgsRef.current?.warning || "Please move away from this content.";
      
      if (isHarsh){
      forcePictureInPictureWarning(msgText);
    }
      // Fire OS Notification over other browser tabs/apps
      sendWarningNotification({
        title: "YTG — Gentle Nudge",
        body: result.description ? `${msgText} (Detected: ${result.description})` : msgText,
      });

      setState("warning");
    } else {
      setState("clear");
    }
    if (result.points_awarded) {
      sendWarningNotification({body: `${warningMessages.applause} (25 points given!)`});
    }
    setLastResult(result);
    return result;
  }

  useEffect(() => () => stop(), []);

  return { start, stop, running, lastResult, state };
}