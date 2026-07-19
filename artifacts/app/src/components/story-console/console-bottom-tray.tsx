import { useState, type FormEvent } from "react";
import { Clock3, MessageSquareText, Mic2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { GenerationCheckpoint } from "@/lib/api";
import type { WorkspaceActivity } from "./story-console-utils";

type ChatMessage = { role: "assistant" | "user"; text: string };

export function ConsoleBottomTray({
  latestJobLabel,
  messages,
  prompt,
  setPrompt,
  onSubmit,
  latestAudioCheckpoint,
  activityItems = [],
}: {
  latestJobLabel?: string | null;
  messages: ChatMessage[];
  prompt: string;
  setPrompt: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  latestAudioCheckpoint: GenerationCheckpoint | null;
  activityItems?: WorkspaceActivity[];
}) {
  const [tab, setTab] = useState("assistant");

  return (
    <section className="rounded-[24px] border border-border bg-white shadow-[0_18px_40px_rgba(0,0,0,0.03)]">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          {latestJobLabel ? `Running now: ${latestJobLabel}` : "Activity"}
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="p-4">
        <TabsList className="grid w-full grid-cols-3 bg-muted">
          <TabsTrigger value="assistant" className="gap-2">
            <MessageSquareText className="h-3.5 w-3.5" />
            Assistant
          </TabsTrigger>
          <TabsTrigger value="logs" className="gap-2">
            <Clock3 className="h-3.5 w-3.5" />
            Logs
          </TabsTrigger>
          <TabsTrigger value="audio" className="gap-2">
            <Mic2 className="h-3.5 w-3.5" />
            Audio
          </TabsTrigger>
        </TabsList>
        <TabsContent value="assistant" className="mt-4">
          <div className="flex flex-wrap gap-2">
            {["open outline", "story text", "approve outline", "generate story", "regenerate"].map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => {
                  if (chip === "open outline") setTab("assistant");
                }}
                className="rounded-[9999px] border border-[#e6e6e7] bg-[#f8f8f8] px-3 py-1 text-[11px] font-semibold text-[#323232] hover:bg-[#e6ffc8]"
              >
                {chip}
              </button>
            ))}
          </div>
          <div className="mt-3 flex gap-3 overflow-x-auto pb-1">
            {messages.slice(-6).map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`min-w-[220px] rounded-[14px] border px-3 py-2 text-xs leading-5 ${
                  message.role === "assistant" ? "border-[#e6e6e7] bg-[#f8f8f8] text-[#323232]" : "border-[#083300] bg-[#96ff1a] text-[#083300]"
                }`}
              >
                {message.text}
              </div>
            ))}
          </div>
          <form onSubmit={onSubmit} className="mt-4 flex gap-2">
            <Input value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Ask the console to act" className="h-10" />
            <Button type="submit" variant="lime" size="sm">
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </TabsContent>
        <TabsContent value="logs" className="mt-4">
          <div className="space-y-2">
            {activityItems.length > 0 ? activityItems.map((item) => (
              <div
                key={`${item.title}-${item.timestamp ?? item.detail}`}
                className={`rounded-[16px] border p-3 ${
                  item.tone === "danger"
                    ? "border-red-200 bg-red-50 text-red-800"
                    : item.tone === "success"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : item.tone === "warning"
                        ? "border-amber-200 bg-amber-50 text-amber-800"
                        : item.tone === "accent"
                          ? "border-[color:#083300] bg-[color:#f5ffd8] text-[color:#083300]"
                          : "border-border bg-muted/30 text-foreground"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold">{item.title}</div>
                  {item.timestamp ? <div className="text-[11px] opacity-65">{new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div> : null}
                </div>
                <div className="mt-1 text-xs leading-5 opacity-80">{item.detail}</div>
              </div>
            )) : (
              <div className="rounded-[16px] border border-dashed border-border bg-muted/20 p-4 text-sm leading-6 text-muted-foreground">
                No activity yet.
              </div>
            )}
          </div>
        </TabsContent>
        <TabsContent value="audio" className="mt-4">
          {latestAudioCheckpoint?.narration_audio_url ? (
            <div className="space-y-3">
              <audio controls className="w-full" src={latestAudioCheckpoint.narration_audio_url} />
              <p className="line-clamp-4 text-sm leading-6 text-[#323232]">
                {latestAudioCheckpoint.narration_text || "Narration is available for this checkpoint."}
              </p>
              <div className="flex flex-wrap gap-2 text-[11px] text-[#71737a]">
                <span className="rounded-[9999px] border border-[#e6e6e7] px-2 py-1">batch {latestAudioCheckpoint.batch_number}</span>
                <span className="rounded-[9999px] border border-[#e6e6e7] px-2 py-1">{latestAudioCheckpoint.narration_voice || "voice"}</span>
              </div>
            </div>
          ) : (
            <div className="rounded-[14px] border border-dashed border-[#e6e6e7] bg-[#f8f8f8] p-4 text-sm leading-6 text-[#71737a]">
              Audio appears here after narrated checkpoints complete.
            </div>
          )}
        </TabsContent>
      </Tabs>
    </section>
  );
}
