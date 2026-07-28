import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { ensureNotificationPermission, sendWarningNotification } from "@/lib/notify";
import { set } from "date-fns";

export function useScanLoop(sessionId: string | null, intervalMs = 5000, warningMessages:any) {
  
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<any>(null);
  const runningRef = useRef(false); // ref, not state — avoids stale closure in setTimeout
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);
  const [state, setState] = useState("");

  async function start(sessId:string|null=null) {
    if (!sessionId && sessId === null) throw new Error("No sessionId — create the session first");
    if (!sessionId && sessId !== null) {sessionId = sessId}
    console.log(`CURRENT SESSION ID AFTER START: ${sessionId}`);
    // 1. Ask the browser for screen share (must be triggered by a user click)
    const media = await navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: 5 },
      audio: false,
    });
    streamRef.current = media;

    // 2. Create a hidden <video> to render the stream so we can draw it to canvas
    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.srcObject = media;
    await video.play();
    videoRef.current = video;

    // 3. Create the canvas we'll snapshot into
    canvasRef.current = document.createElement("canvas");

    // 4. If the user hits the browser's "Stop sharing" button, tear down
    media.getVideoTracks()[0].addEventListener("ended", stop);

    runningRef.current = true;
    setRunning(true);
    tick(); // fire once immediately, then loop
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

  async function tick() {
    if (!runningRef.current) return;
    try {
      await captureAndSend();
    } catch (e) {
      console.error("scan tick failed", e);
    }
    if (runningRef.current) {
        // setState("cooldown");
        timerRef.current = setTimeout(tick, intervalMs);
    }
  }

  async function captureAndSend() {
    const v = videoRef.current;
    const c = canvasRef.current;
    if (!v || !c || !sessionId) return;

    const w = v.videoWidth;
    const h = v.videoHeight;
    if (!w || !h) return; // stream not ready yet

    c.width = w;
    c.height = h;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(v, 0, 0, w, h);

    // toBlob is async — wrap in a Promise
    const blob: Blob | null = await new Promise((res) =>
      c.toBlob(res, "image/png")
    );
    if (!blob) return;

    // POST as multipart/form-data — do NOT set Content-Type manually,
    // the browser adds the correct boundary.
    const result = await api.scan(sessionId, blob);
    setLastResult(result);
    const is_flagged = result.flagged;
    if (is_flagged === true){
      sendWarningNotification(
        {
        body: warningMessages.warning,
      }
      );
        //alert(warningMessages.warning);
        setState("warning");
    }
    else {setState("clear");}
    console.log(result);
    console.log(`THE AI RESPONSE: ${result.description}`);
    return result;
  }

  // Cleanup on unmount
  useEffect(() => () => stop(), []);

  return { start, stop, running, lastResult, state };
}
