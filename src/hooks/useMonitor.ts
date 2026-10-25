import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { GameEvent, ScanResult } from "@/lib/types";

export const SCAN_INTERVAL_MS = 5000;
const MAX_FRAME_WIDTH = 1280;
const MAX_CONSECUTIVE_FAILURES = 3;

// "still": the screen hasn't changed, so nothing is earned until it does
export type MonitorState = "idle" | "starting" | "clear" | "still" | "warning" | "recovering";

export interface ScanLogEntry extends ScanResult {
  at: number;
}

interface Options {
  onResult?: (result: ScanResult) => void;
  /** Game events from starting the session, such as a first-session badge. */
  onStarted?: (events: GameEvent[]) => void;
  /** Called when monitoring ends for any reason other than the user pressing stop. */
  onStopped?: (reason: string) => void;
}

/** Shares the screen, sends a frame to the backend every few seconds and tracks the outcome. */
export function useMonitor({ onResult, onStarted, onStopped }: Options = {}) {
  const [state, setState] = useState<MonitorState>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [log, setLog] = useState<ScanLogEntry[]>([]);
  const [earned, setEarned] = useState(0);
  const [lost, setLost] = useState(0);

  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionRef = useRef<string | null>(null);
  const failuresRef = useRef(0);
  // Keep the latest callbacks without restarting the loop
  const callbacks = useRef({ onResult, onStarted, onStopped });
  callbacks.current = { onResult, onStarted, onStopped };

  const teardown = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    videoRef.current = null;
    sessionRef.current = null;
    setSessionId(null);
    setState("idle");
  }, []);

  const stop = useCallback(
    async (reason?: string) => {
      const id = sessionRef.current;
      teardown();
      if (id) await api.stopSession(id).catch(() => {});
      if (reason) callbacks.current.onStopped?.(reason);
    },
    [teardown],
  );

  const captureFrame = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return null;
    const scale = Math.min(1, MAX_FRAME_WIDTH / video.videoWidth);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  }, []);

  const tick = useCallback(async () => {
    const id = sessionRef.current;
    if (!id) return;
    try {
      const frame = await captureFrame();
      if (frame) {
        const result = await api.scan(id, frame);
        if (sessionRef.current !== id) return; // stopped while the scan was in flight
        failuresRef.current = 0;
        setLog((prev) => [{ ...result, at: Date.now() }, ...prev].slice(0, 30));
        setEarned((n) => n + result.points_awarded);
        setLost((n) => n + result.points_lost);
        if (!result.analysis_failed) {
          setState(
            result.warning_active
              ? result.flagged
                ? "warning"
                : "recovering"
              : result.idle
                ? "still"
                : "clear",
          );
        }
        callbacks.current.onResult?.(result);
        if (result.shutdown) {
          await stop(
            "Your screen hasn't changed for a while, so the session was paused. Start again when you're back.",
          );
          return;
        }
      }
    } catch (error) {
      if (
        error instanceof ApiError &&
        (error.status === 409 || error.status === 403 || error.status === 404)
      ) {
        await stop(error.message);
        return;
      }
      // Scanned too soon after the previous one (e.g. the tab was throttled): just wait for the next tick
      if (!(error instanceof ApiError && error.status === 429)) failuresRef.current += 1;
      if (failuresRef.current >= MAX_CONSECUTIVE_FAILURES) {
        await stop(
          `Monitoring stopped: ${error instanceof Error ? error.message : "the server isn't responding"}`,
        );
        return;
      }
    }
    if (sessionRef.current === id) timerRef.current = setTimeout(tick, SCAN_INTERVAL_MS);
  }, [captureFrame, stop]);

  const start = useCallback(async () => {
    if (sessionRef.current) return;
    setState("starting");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 5 },
        audio: false,
      });
    } catch {
      setState("idle");
      throw new Error("Screen sharing is needed to start a session.");
    }

    try {
      const { session, events } = await api.startSession();
      const video = document.createElement("video");
      video.muted = true;
      video.playsInline = true;
      video.srcObject = stream;
      await video.play();

      streamRef.current = stream;
      videoRef.current = video;
      sessionRef.current = session.id;
      failuresRef.current = 0;
      setSessionId(session.id);
      setLog([]);
      setEarned(0);
      setLost(0);
      setState("clear");
      // The browser's own "stop sharing" button ends the session too
      stream.getVideoTracks()[0]?.addEventListener("ended", () => stop("Screen sharing ended."));
      timerRef.current = setTimeout(tick, 1000);
      callbacks.current.onStarted?.(events);
    } catch (error) {
      stream.getTracks().forEach((t) => t.stop());
      setState("idle");
      throw error;
    }
  }, [stop, tick]);

  // Leaving the page ends the session
  useEffect(
    () => () => {
      const id = sessionRef.current;
      teardown();
      if (id) api.stopSession(id).catch(() => {});
    },
    [teardown],
  );

  return {
    state,
    running: state !== "idle" && state !== "starting",
    sessionId,
    log,
    earned,
    lost,
    start,
    stop: () => stop(),
  };
}
