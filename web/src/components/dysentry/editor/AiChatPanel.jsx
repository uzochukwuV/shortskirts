import React, { useEffect, useRef, useState } from "react";
import { FileText, Plus, Send, Sparkles } from "lucide-react";

function patchPreview(scenePatch) {
  if (!scenePatch) return "";
  return [
    scenePatch.title ? `Title: ${scenePatch.title}` : "",
    scenePatch.description ? `Script: ${scenePatch.description}` : "",
    scenePatch.narration ? `Narration: ${scenePatch.narration}` : "",
    scenePatch.visual_prompt ? `Visual prompt: ${scenePatch.visual_prompt}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
}

export default function AiChatPanel({
  series,
  characters,
  scene,
  requestAssistant,
  onApplyScenePatch,
  onAddSceneFromPatch,
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const send = async () => {
    if (!input.trim() || sending || !scene) return;
    const userMessage = { role: "user", text: input.trim() };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    try {
      const response = await requestAssistant(input.trim());
      const scenePatch = response.scene_patch || {};
      const preview = patchPreview(scenePatch);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: response.message || "Drafted a scene revision.",
          scenePatch,
          preview,
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: error.message || "Sorry, I couldn't generate a revision. Please try again.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col lg:h-full">
      <div className="flex items-center gap-2 border-b border-mist px-5 py-4">
        <Sparkles className="h-4 w-4 text-signal" />
        <h3 className="text-[14px] font-medium tracking-tight-bold text-ink">AI assistant</h3>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {messages.length === 0 && (
          <div className="pt-8 text-center">
            <Sparkles className="mx-auto h-8 w-8 text-ash" />
            <p className="mt-3 text-[13px] text-steel" style={{ lineHeight: 1.5 }}>
              Ask me to rewrite the current scene, tighten narration, or draft the next beat.
            </p>
            {!!characters.length && (
              <p className="mt-2 text-[12px] text-ash">
                Context loaded for {series?.title} and {characters.length} character{characters.length === 1 ? "" : "s"}.
              </p>
            )}
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[88%] rounded-2xl px-4 py-2.5 text-[14px] ${message.role === "user" ? "bg-ink text-white" : "bg-muted text-ink"}`}
              style={{ lineHeight: 1.5 }}
            >
              <p className="whitespace-pre-wrap">{message.text}</p>
              {message.preview && (
                <div className="mt-3 rounded-xl border border-fog bg-white px-3 py-3 text-[12px] text-steel">
                  <p className="mb-2 text-[11px] font-medium uppercase tracking-tight-bold text-steel">
                    Drafted patch
                  </p>
                  <p className="whitespace-pre-wrap">{message.preview}</p>
                </div>
              )}
              {message.role === "assistant" && message.scenePatch && (
                <div className="mt-3 flex gap-3 border-t border-fog/60 pt-2">
                  <button
                    onClick={() => onApplyScenePatch(message.scenePatch)}
                    className="inline-flex items-center gap-1 text-[12px] text-signal transition-colors hover:text-[#1557b8]"
                  >
                    <FileText className="h-3.5 w-3.5" /> Apply to scene
                  </button>
                  <button
                    onClick={() => onAddSceneFromPatch(message.scenePatch)}
                    className="inline-flex items-center gap-1 text-[12px] text-steel transition-colors hover:text-ink"
                  >
                    <Plus className="h-3.5 w-3.5" /> New scene
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-muted px-4 py-2.5 text-[14px] text-steel">Thinking…</div>
          </div>
        )}
      </div>

      <div className="border-t border-mist p-3">
        <div className="flex items-end gap-2 rounded-lg border border-fog bg-white px-3 py-2 focus-within:border-ash">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send();
              }
            }}
            placeholder={scene ? "Ask the assistant to revise this scene…" : "Select a scene to start editing"}
            rows={1}
            disabled={!scene}
            className="flex-1 resize-none bg-transparent text-[14px] text-ink outline-none placeholder-steel disabled:cursor-not-allowed disabled:opacity-60"
            style={{ lineHeight: 1.5, maxHeight: 120 }}
          />
          <button
            onClick={send}
            disabled={sending || !input.trim() || !scene}
            className="shrink-0 rounded-md bg-signal p-2 text-white transition-colors hover:bg-[#1557b8] disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
