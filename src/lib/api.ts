// YTG API client. Configure via VITE_API_BASE_URL, defaults to localhost:8000.
export const API_BASE_URL =
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE_URL) ||
  "http://localhost:8000";

async function jfetch<T = any>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  const ct = res.headers.get("content-type") || "";
  return (ct.includes("json") ? res.json() : (res.text() as any)) as Promise<T>;
}

export const api = {
  // Auth
  signup: (body: { username: string; email: string; password: string, user_type: string }) =>
    jfetch(`/auth/signup`, { method: "POST", body: JSON.stringify(body) }),
  login: (body: { username: string; password: string }) =>
    jfetch(`/auth/login`, { method: "POST", body: JSON.stringify(body) }),

  // Users
  getUser: (userId: string) => jfetch(`/users/${userId}`),

  getConnectionIfUserHasOne: (userId: string) => jfetch(`/users/get/user/connection/${userId}`),

  getUserByNumberId: (userId: number) => jfetch(`/users/number/${userId}`),


  updateUserName: (userId: string, new_name: string) =>
    jfetch(`/users/${userId}/name`, { method: "PATCH", body: JSON.stringify({ new_name }) }),

  usersByGuardian: (guardianId: string) => jfetch(`/users/guardian/${guardianId}`),

  // Guardians
  createGuardian: (body: { owner_id: string; name: string; guardian_type: "family" | "personal" | "dependent"}) =>
    jfetch(`/guardians/create`, { method: "POST", body: JSON.stringify(body) }),

  getGuardian: (id: string) => jfetch(`/guardians/${id}`),
 

  getGuardianByOwner: (userId: string) => jfetch(`/guardians/owner/${userId}`),


  connections: (id: string) => jfetch(`/guardians/${id}/connections`),

  addConnection: (id: string, body: { user_number_id:number,  relationship: string }) =>
    jfetch(`/guardians/${id}/connections/add`, { method: "POST", body: JSON.stringify(body) }),

  removeConnection: (id: string, userId: string|number) =>
    jfetch(`/guardians/${id}/connections/${userId}`, { method: "DELETE" }),
  addRestriction: (id: string, restriction: string) =>
    jfetch(`/guardians/${id}/restrictions/add`, {
      method: "POST",
      body: JSON.stringify({ restriction }),
    }),
  removeRestriction: (id: string, restriction: string) =>
    jfetch(`/guardians/${id}/restrictions/remove`, {
      method: "POST",
      body: JSON.stringify({ restriction }),
    }),
  getSettings: (id: string) => jfetch(`/guardians/${id}/settings`),

  updateSettings: (id: string, body: Record<string, any>) =>
    jfetch(`/guardians/${id}/settings/update`, { method: "PATCH", body: JSON.stringify(body) }),
  
  reports: (id: string) => jfetch(`/guardians/reports/${id}`),

  // Sessions
  getUsersSession: (id: string) => jfetch(`/sessions/user/get/${id}`),

  guardianOn: (guardianId: string) =>
    jfetch(`/sessions/${guardianId}/on`, { method: "POST" }),

  guardianOff: (guardianId: string) =>
    jfetch(`/sessions/${guardianId}/off`, { method: "POST" }),

  getOrCreateSession: (body: { user_id: string; guardian_id: string }) =>
    jfetch(`/sessions/create`, { method: "POST", body: JSON.stringify(body) }),

  startSession: (body: { user_id: string; guardian_id: string }) =>
    jfetch(`/sessions/start`, { method: "POST", body: JSON.stringify(body) }),

  stopSession: (body: { user_id: string; guardian_id: string }) =>
    jfetch(`/sessions/stop`, { method: "POST", body: JSON.stringify(body) }),

  getSession: (id: string) => jfetch(`/sessions/${id}`),

  guardianSessions: (guardianId: string) => jfetch(`/sessions/guardian/${guardianId}`),

  deleteSession: (id: string) => jfetch(`/sessions/${id}`, { method: "DELETE" }),

  flushSession: (id: string) => jfetch(`/sessions/${id}/flush`, { method: "POST" }),
  
  fetchRestrictions: (id: string) => jfetch(`/guardians/restrictions/get/${id}`, {method: "GET"}),

  scan: async (sessionId: string, blob: Blob) => {
    const fd = new FormData();
    fd.append("file", blob, "frame.png");
    const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/scan`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) throw new Error(`scan failed: ${res.status}`);
    return res.json() as Promise<{
      flagged: boolean;
      description: string;
      warning_active: boolean;
      points_awarded: boolean;
    }>;
  },

  // Gamify
  addPoints: (userId: string, amount: number) =>
    jfetch(`/gameify/users/${userId}/points/add`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  removePoints: (userId: string, amount: number) =>
    jfetch(`/gameify/users/${userId}/points/remove`, {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  listRewards: () => jfetch(`/gameify/rewards`),
  buyReward: (userId: string, reward_id: string) =>
    jfetch(`/gameify/users/${userId}/rewards/buy`, {
      method: "POST",
      body: JSON.stringify({ reward_id }),
    }),
};

// Local session (client-side only; real auth handled by backend later)
const KEY = "ytg.session.v1";
export type LocalSession = {
  //id: string;
  user_id: string;
  username: string;
  role: "guardian" | "individual";
  guardian_id?: string;
  points?: number;
};
export const localSession = {
  get(): LocalSession | null {
    if (typeof window === "undefined") return null;
    try {
      return JSON.parse(localStorage.getItem(KEY) || "null");
    } catch {
      return null;
    }
  },
  set(s: LocalSession | null) {
    if (typeof window === "undefined") return;
    if (!s) localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, JSON.stringify(s));
  },
  patch(p: Partial<LocalSession>) {
    const cur = localSession.get();
    if (!cur) return;
    localSession.set({ ...cur, ...p });
  },
  clear() {
    if (typeof window === "undefined") return;
    localStorage.removeItem(KEY);
  },
};

// Extract an id from a variety of backend response shapes.
export function pickId(r: any, ...keys: string[]): string | null {
  if (!r || typeof r !== "object") return null;
  for (const k of keys) {
    const v = r[k];
    if (typeof v === "string" && v) return v;
  }
  return null;
}
