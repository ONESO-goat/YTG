import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

/** After anything that changes the balance, refetch the user so points stay in sync everywhere. */
export function useRefreshBalance() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: meQueryKey });
}
