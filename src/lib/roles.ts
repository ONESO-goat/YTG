import type { Me } from "./types";

/**
 * personal: owns a personal guardian and monitors themself
 * family-owner: a caregiver who owns a family guardian and watches over its members
 * member: a dependent connected to someone else's family guardian
 */
export type Role = "personal" | "family-owner" | "member";

export function roleOf(me: Me): Role {
  if (!me.is_guardian_owner) return "member";
  return me.guardian?.guardian_type === "family" ? "family-owner" : "personal";
}
