import React, { useEffect, useRef, useState } from "react";
import { FileText, Plus, Send, Sparkles, Loader2 } from "lucide-react";

const QUICK_PROMPTS = [
  "Tighten the visual prompt for stronger composition",
  "Rewrite narration in a calmer tone",
  "Make this scene more cinematic and atmospheric",
  "Draft the next beat after this scene",
];

function patchPreview(scenePatch) {
  if (!scenePatch) return "";
  return [
    scenePatch.title ? `Title: ${scenePatch.title}` : "",
    scenePatch.description ? `Script: ${scenePatch.description}` : "",
    scenePatch.narration ? `Narration: ${scenePatch.narration}` : "",
    scenePatch.visual_prompt ? `Visual prompt: ${scenePatch.visual_prompt}` : "",
    scenePatch.mood ? `Mood: ${scenePatch.mood}` : "",
    scenePatch.location ? `Location: ${scenePatch.location}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
}

function hasPatchContent(scenePatch) {
  if (!scenePatch || typeof scenePatch !== "object") return false;
  return Object.values(scenePatch).some((v) => typeof v === "string" && v.trim());
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
  const sceneId = scene?.id;

  // Clear chat when switching scenes so patches don't get applied to the wrong one.
  useEffect(() => {
    setMessages([]);
    setInput("");
  }, [sceneId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const send = async (text) => {
    const instruction = (text ?? input).trim();
    if (!instruction || sending || !scene) return;

    const userMessage = { role: "user", text: instruction };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    try {
      const response = await requestAssistant(instruction);
      const scenePatch = response.scene_patch || {};
      const preview = patchPreview(scenePatch);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: response.message || "Drafted a scene revision.",
          scenePatch: hasPatchContent(scenePatch) ? scenePatch : null,
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
        <div className="min-w-0 flex-1">
          <h3 className="text-[14px] font-medium tracking-tight-bold text-ink">AI assistant</h3>
          <p className="truncate text-[11px] text-steel">
            {scene ? `Editing “${scene.title || "Untitled"}”` : "Select a scene first"}
          </p>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {messages.length === 0 && (
          <div className="pt-4">
            <div className="text-center">
              <Sparkles className="mx-auto h-8 w-8 text-ash" />
              <p className="mt-3 text-[13px] text-steel" style={{ lineHeight: 1.5 }}>
                Ask me to rewrite the current scene, tighten narration, or draft the next beat.
                Suggestions are advisory — you choose what to apply.
              </p>
              {!!characters.length && (
                <p className="mt-2 text-[12px] text-ash">
                  Context loaded for {series?.title} and {characters.length} character
                  {characters.length === 1 ? "" : "s"}.
                </p>
              )}
            </div>

            {scene && (
              <div className="mt-6 space-y-2">
                <p className="text-[11px] font-medium uppercase tracking-tight-bold text-steel">
                  Try
                </p>
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => send(prompt)}
                    disabled={sending}
                    className="block w-full rounded-xl border border-fog bg-white px-3 py-2.5 text-left text-[12px] text-ink transition-colors hover:border-ash hover:bg-muted disabled:opacity-50"
                    style={{ lineHeight: 1.4 }}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[88%] rounded-2xl px-4 py-2.5 text-[14px] ${
                message.role === "user" ? "bg-ink text-white" : "bg-muted text-ink"
              }`}
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
                <div className="mt-3 flex flex-wrap gap-3 border-t border-fog/60 pt-2">
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
            <div className="inline-flex items-center gap-2 rounded-2xl bg-muted px-4 py-2.5 text-[13px] text-steel">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Drafting revision…
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-mist px-4 py-3">
        <div className="flex items-end gap-2 rounded-xl border border-fog bg-white px-3 py-2 focus-within:border-ash">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={!scene || sending}
            rows={2}
            placeholder={scene ? "Ask for a scene revision…" : "Select a scene first"}
            className="max-h-28 flex-1 resize-none bg-transparent py-1 text-[14px] text-ink outline-none placeholder-steel disabled:opacity-50"
            style={{ lineHeight: 1.4 }}
          />
          <button
            onClick={() => send()}
            disabled={!scene || sending || !input.trim()}
            className="mb-0.5 rounded-lg bg-ink p-2 text-white transition-colors hover:bg-[#1f2937] disabled:opacity-40"
            title="Send"
          >
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
        <p className="mt-2 text-[11px] text-ash">Enter to send · Shift+Enter for newline</p>
      </div>
    </div>
  );
}
