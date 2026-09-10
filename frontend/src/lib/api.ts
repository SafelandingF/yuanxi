import type { AgentEvent } from "./agent";
import type { Profile, Candidate, PlanItem } from "./demo";
export interface RankedCandidate extends Candidate {
  score: number;
  strengths: string[];
  conflicts: string[];
  explanation: string;
}
export interface Analysis {
  session_id: string;
  profile: Profile;
  portrait: {
    relationship_type: string;
    summary: string;
    core_preferences: string[];
    possible_conflicts: string[];
  };
  candidates: RankedCandidate[];
  peach: number;
  sample_count: number;
  distribution: { high: number; medium: number; low: number };
}
export interface DateResult {
  plan: PlanItem[];
  budget_limit?: number;
  target_spend?: number;
  spending_style?: string;
  feedback: boolean;
  feedback_explanation: string;
  adjustment: number;
  initial_score: number;
  final_score: number;
  reason: string;
}
export type StreamEvent<T> =
  | AgentEvent
  | { type: "stage"; index: number; label: string }
  | ({ type: "result" } & T)
  | { type: "delta"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

export async function readStream<T>(
  path: string,
  body: unknown,
  signal: AbortSignal,
  receive: (event: StreamEvent<T>) => void,
) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : "本地服务暂时不可用，请确认后端已启动",
    );
  }
  if (!response.body) throw new Error("当前浏览器无法读取流式响应");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "",
    completed = false;
  const process = (block: string) => {
    const lines = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart());
    if (!lines.length) return;
    const event = JSON.parse(lines.join("\n")) as StreamEvent<T>;
    if (event.type === "error") throw new Error(event.message);
    if (event.type === "done") completed = true;
    receive(event);
  };
  try {
    while (true) {
      const { done, value } = await reader.read();
      pending += decoder
        .decode(value, { stream: !done })
        .replace(/\r\n/g, "\n");
      let end: number;
      while ((end = pending.indexOf("\n\n")) !== -1) {
        const block = pending.slice(0, end);
        pending = pending.slice(end + 2);
        process(block);
      }
      if (done) break;
    }
    if (pending.trim()) process(pending);
    if (!completed) throw new Error("生成连接已中断，请重试");
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
