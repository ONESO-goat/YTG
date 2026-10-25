import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { toast } from "sonner";
import { api } from "./api";
import { meQueryKey } from "./auth";
import type { GuardianSettings } from "./types";

export const keys = {
  health: ["health"] as const,
  members: (gid: string) => ["guardian", gid, "members"] as const,
  settings: (gid: string) => ["guardian", gid, "settings"] as const,
  restrictions: (gid: string) => ["guardian", gid, "restrictions"] as const,
  reports: (gid: string) => ["guardian", gid, "reports"] as const,
  mySession: ["session", "me"] as const,
  progress: ["progress", "me"] as const,
  achievements: ["progress", "achievements"] as const,
  leaderboard: (scope: string) => ["progress", "leaderboard", scope] as const,
  rewards: ["rewards"] as const,
  myRewards: ["rewards", "mine"] as const,
};

export const toastError = (error: unknown) =>
  toast.error(error instanceof Error ? error.message : "Something went wrong");

export const useHealth = () =>
  useQuery({ queryKey: keys.health, queryFn: api.health, staleTime: 60_000 });

export const useMembers = (gid: string, enabled = true) =>
  useQuery({
    queryKey: keys.members(gid),
    queryFn: () => api.members(gid),
    enabled,
    refetchInterval: 10_000,
  });

export const useSettings = (gid: string) =>
  useQuery({ queryKey: keys.settings(gid), queryFn: () => api.settings(gid) });

export const useRestrictions = (gid: string) =>
  useQuery({ queryKey: keys.restrictions(gid), queryFn: () => api.restrictions(gid) });

export const useReports = (gid: string, enabled = true) =>
  useQuery({
    queryKey: keys.reports(gid),
    queryFn: () => api.reports(gid),
    enabled,
    refetchInterval: 15_000,
  });

export const useMySession = () => useQuery({ queryKey: keys.mySession, queryFn: api.mySession });

export const useProgress = (enabled = true) =>
  useQuery({ queryKey: keys.progress, queryFn: api.progress, enabled });

export const useAchievements = () =>
  useQuery({ queryKey: keys.achievements, queryFn: api.achievements });

export const useLeaderboard = (scope: "family" | "global", enabled = true) =>
  useQuery({
    queryKey: keys.leaderboard(scope),
    queryFn: () => api.leaderboard(scope),
    enabled,
    refetchInterval: 30_000,
  });

/** After points, XP or badges change, refetch everything that shows them. */
export function useRefreshProgress() {
  const qc = useQueryClient();
  return useCallback(() => {
    qc.invalidateQueries({ queryKey: meQueryKey });
    qc.invalidateQueries({ queryKey: ["progress"] });
  }, [qc]);
}

export const useRewards = () => useQuery({ queryKey: keys.rewards, queryFn: api.rewards });
export const useMyRewards = () => useQuery({ queryKey: keys.myRewards, queryFn: api.myRewards });

export function useUpdateSettings(gid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<GuardianSettings>) => api.updateSettings(gid, body),
    onSuccess: (data) => {
      qc.setQueryData(keys.settings(gid), data);
      toast.success("Settings saved");
    },
    onError: toastError,
  });
}

export function useToggleGuardian(gid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (on: boolean) => api.setGuardianOn(gid, on),
    onSuccess: (g) => {
      qc.invalidateQueries({ queryKey: meQueryKey });
      qc.invalidateQueries({ queryKey: keys.members(gid) });
      qc.invalidateQueries({ queryKey: keys.mySession });
      toast.success(g.on ? "Monitoring is on" : "Monitoring is paused");
    },
    onError: toastError,
  });
}
