import type {
  AuthResponse,
  Connection,
  Guardian,
  GuardianSettings,
  GameEvent,
  Health,
  Leaderboard,
  Me,
  MemberOverview,
  MonitoringSession,
  OwnedReward,
  Progress,
  PurchaseResult,
  Report,
  Restrictions,
  Achievement,
  Reward,
  ScanResult,
  User,
  UserSummary,
  UserType,
} from "./types";

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const TOKEN_KEY = "ytg.token";

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable: the session just won't survive a reload */
    }
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// Called when the backend rejects our token, so the app can sign out
let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: [{loc, msg}, ...]
    if (Array.isArray(detail) && detail[0]?.msg) {
      return detail
        .map((d: { loc?: unknown[]; msg: string }) => `${d.loc?.at(-1) ?? "field"}: ${d.msg}`)
        .join(", ");
    }
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, `Can't reach the YTG server at ${API_BASE_URL}. Is the backend running?`);
  }

  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }

  if (!res.ok) {
    if (res.status === 401 && token) onUnauthorized();
    throw new ApiError(res.status, errorMessage(body, `${res.status} ${res.statusText}`));
  }
  return body as T;
}

const json = (method: string, data?: unknown): RequestInit => ({
  method,
  body: data === undefined ? undefined : JSON.stringify(data),
});

export const api = {
  health: () => request<Health>("/health"),

  // Auth
  signup: (body: { username: string; email: string; password: string; user_type: UserType }) =>
    request<AuthResponse>("/auth/signup", json("POST", body)),
  login: (body: { identifier: string; password: string }) =>
    request<AuthResponse>("/auth/login", json("POST", body)),
  me: () => request<Me>("/auth/me"),

  // Account
  updateName: (new_name: string) => request<User>("/users/me/name", json("PATCH", { new_name })),
  changePassword: (current_password: string, new_password: string) =>
    request<User>("/users/me/password", json("PUT", { current_password, new_password })),
  lookupDependent: (numberId: number) => request<UserSummary>(`/users/number/${numberId}`),

  // Guardians
  createGuardian: (name: string) => request<Guardian>("/guardians", json("POST", { name })),
  setGuardianOn: (id: string, on: boolean) =>
    request<Guardian>(`/guardians/${id}/${on ? "on" : "off"}`, json("POST")),
  members: (id: string) => request<MemberOverview[]>(`/guardians/${id}/members`),
  addMember: (id: string, user_number_id: number) =>
    request<Connection>(
      `/guardians/${id}/members`,
      json("POST", { user_number_id, relationship: "offspring" }),
    ),
  removeMember: (id: string, userId: string) =>
    request<{ message: string }>(`/guardians/${id}/members/${userId}`, json("DELETE")),
  settings: (id: string) => request<GuardianSettings>(`/guardians/${id}/settings`),
  updateSettings: (id: string, body: Partial<GuardianSettings>) =>
    request<GuardianSettings>(`/guardians/${id}/settings`, json("PATCH", body)),
  restrictions: (id: string) => request<Restrictions>(`/guardians/${id}/restrictions`),
  addRestriction: (id: string, restriction: string) =>
    request<Restrictions>(`/guardians/${id}/restrictions`, json("POST", { restriction })),
  removeRestriction: (id: string, restriction: string) =>
    request<Restrictions>(
      `/guardians/${id}/restrictions?restriction=${encodeURIComponent(restriction)}`,
      json("DELETE"),
    ),
  reports: (id: string) => request<Report[]>(`/guardians/${id}/reports`),
  deleteReport: (id: string, reportId: string) =>
    request<{ message: string }>(`/guardians/${id}/reports/${reportId}`, json("DELETE")),

  // Monitoring sessions
  mySession: () => request<MonitoringSession | null>("/sessions/me"),
  startSession: () =>
    request<{ session: MonitoringSession; events: GameEvent[] }>(
      "/sessions/start",
      json("POST", {}),
    ),
  stopSession: (id: string) => request<MonitoringSession>(`/sessions/${id}/stop`, json("POST")),
  scan: (sessionId: string, frame: Blob) => {
    const form = new FormData();
    form.append("file", frame, "frame.png");
    return request<ScanResult>(`/sessions/${sessionId}/scan`, { method: "POST", body: form });
  },
  grant: (points: number, xp: number) =>
    request<{ currency: number; events: GameEvent[] }>("/dev/grant", json("POST", { points, xp })),
  simulate: (category: string, scans: number) =>
    request<{ remaining: number; category: string }>(
      "/dev/simulate",
      json("POST", { category, scans }),
    ),

  // Progress
  progress: () => request<Progress>("/progress/me"),
  achievements: () => request<Achievement[]>("/progress/me/achievements"),
  leaderboard: (scope: "family" | "global") =>
    request<Leaderboard>(`/progress/leaderboard?scope=${scope}`),
  updatePreferences: (body: { timezone?: string; show_on_leaderboard?: boolean }) =>
    request<Progress>("/progress/me/preferences", json("PATCH", body)),

  // Shop
  rewards: () => request<Reward[]>("/gameify/rewards"),
  myRewards: () => request<OwnedReward[]>("/gameify/me/rewards"),
  buyReward: (id: string) => request<PurchaseResult>(`/gameify/rewards/${id}/buy`, json("POST")),
  refundReward: (ownedId: string) =>
    request<PurchaseResult>(`/gameify/me/rewards/${ownedId}/refund`, json("POST")),
};
