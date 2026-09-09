import type { Profile } from "./demo";
import type { Analysis, DateResult, RankedCandidate } from "./api";
export interface Preferences {
  city: string | null;
  age_min: number | null;
  age_max: number | null;
  interests: string[];
  companionship: string | null;
  goal: string | null;
}
export interface AgentCard {
  component:
    | "profile"
    | "preferences"
    | "candidates"
    | "comparison"
    | "selection"
    | "empty";
  revision: number;
  props: Record<string, any>;
}
export interface AgentPart {
  type: "text" | "tool_start" | "tool_end" | "card";
  text?: string;
  id?: string;
  name?: string;
  label?: string;
  input?: unknown;
  output?: unknown;
  status?: "success" | "error";
  summary?: string;
  duration_ms?: number;
  card?: AgentCard;
}
export interface AgentTurn {
  id: string;
  user: string;
  parts: AgentPart[];
  failed?: boolean;
}
export interface AgentSession {
  latest_date?: {
    request: {
      candidate_id: number;
      budget: number;
      start: string;
      meal_preference: string;
      food_restrictions: string[];
    };
    result: DateResult;
    summary: string;
  };
  session_id: string;
  profile: Profile;
  portrait: Analysis["portrait"] | null;
  preferences: Preferences;
  revision: number;
  candidates: RankedCandidate[];
  selected_id: number | null;
  turns: AgentTurn[];
}
export type AgentEvent =
  | { type: "state"; session: AgentSession }
  | { type: "card"; card: AgentCard }
  | ({ type: "tool_start" | "tool_end" } & Omit<AgentPart, "type">);
export async function sessionRequest(
  path: string,
  body?: unknown,
): Promise<AgentSession> {
  const response = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || "无法连接本地服务");
  return data;
}
export function preferenceLabels(p: Preferences): string[] {
  return [
    p.city ? `${p.city}同城` : "城市不限",
    p.age_min || p.age_max
      ? `${p.age_min || 18}–${p.age_max || 80} 岁`
      : "年龄不限",
    ...p.interests,
    p.companionship,
    p.goal,
  ].filter(Boolean) as string[];
}
