import { useState, type FormEvent } from "react";
import { MessageSquareText, Mic2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { GenerationCheckpoint } from "@/lib/api";

type ChatMessage = { role: "assistant" | "user"; text: string };

export function ConsoleBottomTray({
  latestJobLabel,
  messages,
  prompt,
  setPrompt,
  onSubmit,
  latestAudioCheckpoint,
}: {
  latestJobLabel?: string | null;
  messages: ChatMessage[];
  prompt: string;
  setPrompt: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  latestAudioCheckpoint: GenerationCheckpoint | null;
}) {
  const [tab, setTab] = useState("assistant");

  return (
    <section className="rounded-[24px] border border-[#e6e6e7] bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-[#e6e6e7] px-4 py-3">
        <div className="text-[11px] font-bold uppercase text-[#71737a]">
          {latestJobLabel ? `Running now: ${latestJobLabel}` : "Activity"}
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab} className="p-4">
        <TabsList className="grid w-full grid-cols-2 bg-[#f2f1f0]">
          <TabsTrigger value="assistant" className="gap-2">
            <MessageSquareText className="h-3.5 w-3.5" />
            Assistant
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
