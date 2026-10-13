"use client";

import { useState } from "react";
import Agent from "@/components/Agent";
import Chat from "@/components/Chat";

const TABS = [
  { id: "chat", label: "Chat (stream + cache)" },
  { id: "agent", label: "Agent (LangGraph)" },
] as const;

export default function Shell() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("chat");

  return (
    <div className="flex h-full flex-col gap-3">
      <nav className="flex gap-1 border-b border-neutral-200 dark:border-neutral-800">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              tab === t.id
                ? "border-blue-600 font-medium"
                : "border-transparent text-neutral-500"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <div className={tab === "chat" ? "min-h-0 flex-1" : "hidden"}>
        <Chat />
      </div>
      <div className={tab === "agent" ? "min-h-0 flex-1" : "hidden"}>
        <Agent />
      </div>
    </div>
  );
}