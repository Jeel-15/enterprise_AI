"use client";

import { useEffect, useRef, useState } from "react";
import { getProviders, streamChat, type ChatEvent } from "@/lib/api";

type Meta = {
  source: "cache" | "llm";
  provider: string | null;
  latencyMs: number;
  ttftMs: number | null;
};

type Msg = {
  id: number;
  role: "user" | "assistant";
  content: string;
  meta?: Meta;
  error?: string;
  streaming?: boolean;
};

function Badge({ meta }: { meta: Meta }) {
  const isCache = meta.source === "cache";
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
      <span
        className={`rounded-full px-2 py-0.5 font-medium ${
          isCache
            ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
            : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
        }`}
      >
        {isCache ? "⚡ cache hit" : `LLM${meta.provider ? ` · ${meta.provider}` : ""}`}
      </span>
      <span className="text-neutral-500">total {Math.round(meta.latencyMs)} ms</span>
      {meta.ttftMs !== null && (
        <span className="text-neutral-500">first token {Math.round(meta.ttftMs)} ms</span>
      )}
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [useCache, setUseCache] = useState(true);
  const [provider, setProvider] = useState("");
  const [providers, setProviders] = useState<string[]>([]);
  const [apiError, setApiError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => {
    getProviders()
      .then((p) =>
        setProviders(
          Object.entries(p.available)
            .filter(([, v]) => v.ready)
            .map(([name]) => name),
        ),
      )
      .catch((e: Error) =>
        setApiError(`Backend sathe connect nathi thatu (${e.message}). FastAPI chalu 6e?`),
      );
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "auto" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;

    const botId = nextId.current + 1;
    const userMsg: Msg = { id: nextId.current, role: "user", content: text };
    const botMsg: Msg = { id: botId, role: "assistant", content: "", streaming: true };
    nextId.current += 2;

    setMessages((ms) => [...ms, userMsg, botMsg]);
    setInput("");
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;

    const patch = (fn: (m: Msg) => Msg) =>
      setMessages((ms) => ms.map((m) => (m.id === botId ? fn(m) : m)));

    const onEvent = (e: ChatEvent) => {
      if (e.type === "token") {
        patch((m) => ({ ...m, content: m.content + e.text }));
      } else if (e.type === "done") {
        patch((m) => ({
          ...m,
          streaming: false,
          meta: {
            source: e.source,
            provider: e.provider,
            latencyMs: e.latency_ms,
            ttftMs: e.ttft_ms,
          },
        }));
      } else if (e.type === "error") {
        patch((m) => ({ ...m, streaming: false, error: e.message }));
      }
    };

    try {
      await streamChat(
        { message: text, provider: provider || null, use_cache: useCache },
        onEvent,
        controller.signal,
      );
    } catch (err) {
      const e = err as Error;
      if (e.name === "AbortError") {
        patch((m) => ({ ...m, streaming: false }));
      } else {
        patch((m) => ({ ...m, streaming: false, error: e.message }));
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  return (
    <div className="flex h-full flex-col gap-3">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-lg font-semibold">Enterprise AI Chat</h1>
        <div className="flex flex-wrap items-center gap-3 text-sm">
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
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={useCache}
              onChange={(e) => setUseCache(e.target.checked)}
            />
            Semantic cache
          </label>
        </div>
      </header>

      {apiError && (
        <div className="rounded border border-red-300 bg-red-50 p-2 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          {apiError}
        </div>
      )}

      <div className="flex-1 space-y-4 overflow-y-auto rounded border border-neutral-200 p-3 dark:border-neutral-800">
        {messages.length === 0 && (
          <p className="text-sm text-neutral-500">
            Kai pan puchho. Same sawal fari puchho to cache hit dekhase.
          </p>
        )}
        {messages.map((m) => (
          <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex"}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                m.role === "user"
                  ? "bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-900"
                  : "bg-neutral-100 dark:bg-neutral-800"
              }`}
            >
              <div className="whitespace-pre-wrap">
                {m.content}
                {m.streaming && <span className="animate-pulse">▍</span>}
              </div>
              {m.error && <div className="mt-2 text-xs text-red-600">⚠ {m.error}</div>}
              {m.meta && <Badge meta={m.meta} />}
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
              void send();
            }
          }}
          rows={2}
          placeholder="Message lakho... (Enter = send, Shift+Enter = navi line)"
          className="flex-1 resize-none rounded border border-neutral-300 bg-transparent p-2 text-sm dark:border-neutral-700"
        />
        {busy ? (
          <button
            onClick={() => abortRef.current?.abort()}
            className="rounded bg-red-600 px-4 text-sm text-white"
          >
            Stop
          </button>
        ) : (
          <button
            onClick={() => void send()}
            disabled={!input.trim()}
            className="rounded bg-blue-600 px-4 text-sm text-white disabled:opacity-40"
          >
            Send
          </button>
        )}
      </div>
    </div>
  );
}