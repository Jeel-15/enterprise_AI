export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type ChatEvent =
  | { type: "meta"; source: "cache" | "llm" }
  | { type: "token"; text: string }
  | {
      type: "done";
      source: "cache" | "llm";
      provider: string | null;
      latency_ms: number;
      ttft_ms: number | null;
    }
  | { type: "error"; message: string };

export type ProvidersResponse = {
  active: string;
  fallbacks: string;
  available: Record<string, { model: string; ready: boolean }>;
};

export async function getProviders(): Promise<ProvidersResponse> {
  const r = await fetch(`${API_URL}/providers`);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function streamChat(
  body: { message: string; provider?: string | null; use_cache: boolean },
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      if (j.detail) {
        detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      }
    } catch {}
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frame "\n\n" thi puro thay 6e. Adhuri frame buffer ma rahe 6e.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(5).trim()) as ChatEvent);
      } catch {
        // kharab frame ignore
      }
    }
  }
}


export type AgentResult = {
  status: "done" | "waiting_approval";
  thread_id: string;
  answer?: string | null;
  interrupt?: { message: string; question: string };
  trace: string[];
};

async function errorDetail(res: Response): Promise<string> {
  let detail = `HTTP ${res.status}`;
  try {
    const j = await res.json();
    if (j.detail) {
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    }
  } catch {}
  return detail;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json() as Promise<T>;
}

export function runAgent(body: {
  question: string;
  provider?: string | null;
  thread_id?: string | null;
}) {
  return postJson<AgentResult>("/agent", body);
}

export function resumeAgent(threadId: string, approved: boolean) {
  return postJson<AgentResult>(
    `/agent/${encodeURIComponent(threadId)}/resume`,
    { approved },
  );
}