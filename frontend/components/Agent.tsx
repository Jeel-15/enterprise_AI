"use client";

import { useEffect, useRef, useState } from "react";
import {
  getProviders,
  resumeAgent,
  runAgent,
  type AgentResult,
} from "@/lib/api";

type Run = {
  id: number;
  question: string;
  threadId?: string;
  status: "running" | "waiting_approval" | "done" | "error";
  trace: string[];
  answer?: string;
  prompt?: string;
  error?: string;
  deciding?: boolean;
};

const SAMPLES = [
  "What is the refund policy?",
  "Send a refund of 500 dollars to customer John",
  "Delete all data of customer Priya",
];

function fromResult(r: AgentResult): Partial<Run> {
  return {
    threadId: r.thread_id,
    status: r.status,
    trace: r.trace,
    answer: r.answer ?? undefined,
    prompt: r.interrupt?.message,
    error: undefined,
    deciding: false,
  };
}

function StatusChip({ run }: { run: Run }) {
  const map = {
    running: ["bg-neutral-200 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200", "⏳ running..."],
    waiting_approval: ["bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200", "⏸ waiting for approval"],
    done: ["bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200", "✅ done"],
    error: ["bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200", "⚠ error"],
  } as const;
  const [cls, label] = map[run.status];
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

export default function Agent() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [provider, setProvider] = useState("");
  const [providers, setProviders] = useState<string[]>([]);
  const nextId = useRef(1);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getProviders()
      .then((p) =>
        setProviders(
          Object.entries(p.available)
            .filter(([, v]) => v.ready)
            .map(([name]) => name),
        ),
      )
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [runs]);

  const patch = (id: number, p: Partial<Run>) =>
    setRuns((rs) => rs.map((r) => (r.id === id ? { ...r, ...p } : r)));

  async function send(text: string) {
    const q = text.trim();
    if (!q || sending) return;
    const id = nextId.current++;
    setRuns((rs) => [...rs, { id, question: q, status: "running", trace: [] }]);
    setInput("");
    setSending(true);
    try {
      const r = await runAgent({ question: q, provider: provider || null });
      patch(id, fromResult(r));
    } catch (e) {
      patch(id, { status: "error", error: (e as Error).message });
    } finally {
      setSending(false);
    }
  }

  async function decide(run: Run, approved: boolean) {
    if (!run.threadId) return;
    patch(run.id, { deciding: true });
    try {
      const r = await resumeAgent(run.threadId, approved);
      patch(run.id, fromResult(r));
    } catch (e) {
      patch(run.id, {
        status: "error",
        error: (e as Error).message,
        deciding: false,
      });
    }
  }

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <div className="flex flex-wrap gap-2">
          {SAMPLES.map((s) => (
            <button
              key={s}
              onClick={() => setInput(s)}
              className="rounded-full border border-neutral-300 px-3 py-1 text-xs hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
            >
              {s}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1">
          Provider
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="rounded border border-neutral-300 bg-transparent px-2 py-1 dark:border-neutral-700"
          >
            <option value="">default (.env)</option>
            {providers.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto rounded border border-neutral-200 p-3 dark:border-neutral-800">
        {runs.length === 0 && (
          <p className="text-sm text-neutral-500">
            Upar na sample par click karo, ke potano sawal lakho. Normal sawal
            seedho answer aape. Sensitive action (refund, delete, email) par
            graph pause thase.
          </p>
        )}

        {runs.map((run) => (
          <div key={run.id} className="space-y-2">
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-lg bg-neutral-900 px-3 py-2 text-sm text-white dark:bg-neutral-100 dark:text-neutral-900">
                {run.question}
              </div>
            </div>

            <div className="space-y-2 rounded-lg bg-neutral-100 p-3 text-sm dark:bg-neutral-800">
              <StatusChip run={run} />

              {run.trace.length > 0 && (
                <ol className="list-inside list-decimal space-y-0.5 font-mono text-xs text-neutral-600 dark:text-neutral-300">
                  {run.trace.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ol>
              )}

              {run.status === "waiting_approval" && (
                <div className="rounded border border-amber-300 bg-amber-50 p-3 dark:border-amber-700 dark:bg-amber-950">
                  <p className="mb-2">
                    {run.prompt ?? "Approval joiye."}
                  </p>
                  <div className="flex gap-2">
                    <button
                      disabled={run.deciding}
                      onClick={() => void decide(run, true)}
                      className="rounded bg-green-600 px-3 py-1 text-white disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      disabled={run.deciding}
                      onClick={() => void decide(run, false)}
                      className="rounded bg-red-600 px-3 py-1 text-white disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}

              {run.answer && (
                <div className="whitespace-pre-wrap rounded bg-white p-2 dark:bg-neutral-900">
                  {run.answer}
                </div>
              )}

              {run.error && (
                <div className="text-xs text-red-600">⚠ {run.error}</div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(input);
            }
          }}
          rows={2}
          placeholder="Agent ne kaam aapo..."
          className="flex-1 resize-none rounded border border-neutral-300 bg-transparent p-2 text-sm dark:border-neutral-700"
        />
        <button
          onClick={() => void send(input)}
          disabled={sending || !input.trim()}
          className="rounded bg-blue-600 px-4 text-sm text-white disabled:opacity-40"
        >
          {sending ? "..." : "Run"}
        </button>
      </div>
    </div>
  );
}