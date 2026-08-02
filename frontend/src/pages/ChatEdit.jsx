const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import React, { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Send, Sparkles, ArrowLeft, Wand2, Download, Share2, MessageSquareText } from "lucide-react";
import AppLayout from "@/components/AppLayout";

import { refineVideo } from "@/lib/video";
import { cn } from "@/lib/utils";

const QUICK_CHIPS = [
  "Make it slower",
  "Add golden light",
  "More dramatic",
  "Wider shot",
  "Add rain",
  "Warmer tones",
];

export default function ChatEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    db.entities.Video.get(id).then(setVideo);
    db.entities.ChatMessage.filter({ video_id: id }, "created_date", 100).then(setMessages);
    const unsubVideo = db.entities.Video.subscribe((e) => { if (e.data?.id === id) setVideo(e.data); });
    const unsubMsg = db.entities.ChatMessage.subscribe((e) => {
      if (e.data?.video_id !== id) return;
      setMessages((prev) => {
        if (e.type === "create") return [...prev, e.data];
        if (e.type === "update") return prev.map((m) => (m.id === e.data.id ? e.data : m));
        if (e.type === "delete") return prev.filter((m) => m.id !== e.id);
        return prev;
      });
    });
    return () => { unsubVideo(); unsubMsg(); };
  }, [id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (text) => {
    const change = (text ?? input).trim();
    if (!change || busy) return;
    setInput("");
    setBusy(true);
    try {
      await refineVideo(id, change);
    } catch (e) {
      setInput(change);
    } finally {
      setBusy(false);
    }
  };

  const isGenerating = video?.status === "generating";

  return (
    <AppLayout>
      <div className="mb-4 flex items-center gap-2">
        <button onClick={() => navigate(-1)} className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:text-ink">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h1 className="font-display text-lg font-bold tracking-tight sm:text-xl">Chat to edit</h1>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Left: sticky preview + chips */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
            {video?.status === "ready" && video.video_url ? (
              <video src={video.video_url} poster={video.thumbnail_url} controls loop muted playsInline className={`w-full bg-black ${video.aspect_ratio === "9:16" ? "aspect-[9/16]" : video.aspect_ratio === "1:1" ? "aspect-square" : "aspect-video"}`} />
            ) : (
              <div className={`relative flex items-center justify-center bg-secondary ${video?.aspect_ratio === "9:16" ? "aspect-[9/16]" : video?.aspect_ratio === "1:1" ? "aspect-square" : "aspect-video"}`}>
                <div className="absolute inset-0 shimmer opacity-60" />
                <div className="flex flex-col items-center gap-2 text-center">
                  <Sparkles className="h-6 w-6 animate-spin-slow text-ink" />
                  <p className="text-xs text-muted-foreground">Re-rendering…</p>
                </div>
              </div>
            )}
          </div>
          <p className="mt-3 line-clamp-2 text-sm text-ink">{video?.prompt}</p>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {QUICK_CHIPS.map((c) => (
              <button key={c} onClick={() => send(c)} disabled={busy} className="rounded-full border border-border bg-card px-3 py-1 text-[11px] text-muted-foreground hover:border-ink/40 hover:text-ink disabled:opacity-50">
                {c}
              </button>
            ))}
          </div>

          {video?.status === "ready" && (
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button onClick={() => navigate(`/video/${id}/export`)} className="flex items-center justify-center gap-1.5 rounded-xl border border-border bg-card py-2.5 text-xs font-medium hover:border-ink/40"><Download className="h-3.5 w-3.5" /> Export</button>
              <button onClick={() => navigate(`/video/${id}/share`)} className="flex items-center justify-center gap-1.5 rounded-xl border border-border bg-card py-2.5 text-xs font-medium hover:border-ink/40"><Share2 className="h-3.5 w-3.5" /> Share</button>
            </div>
          )}
        </div>

        {/* Right: chat */}
        <div className="flex h-[60vh] flex-col rounded-2xl border border-border bg-card shadow-sm lg:h-[72vh]">
          <div className="flex items-center gap-2 border-b border-border px-4 py-3">
            <Wand2 className="h-4 w-4 text-ink" />
            <p className="text-sm font-semibold">AI editor</p>
            {isGenerating && <span className="ml-auto flex items-center gap-1 text-[11px] text-muted-foreground"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink" /> re-rendering</span>}
          </div>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-ink text-white"><MessageSquareText className="h-4 w-4" /></span>
                <p className="text-sm font-medium">Describe a change</p>
                <p className="max-w-[220px] text-xs text-muted-foreground">Tell the AI how to refine your video. Each edit re-renders with the change applied.</p>
              </div>
            )}
            {messages.map((m) => (
              <motion.div key={m.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div className={cn("max-w-[80%] rounded-2xl px-3.5 py-2 text-sm", m.role === "user" ? "bg-ink text-white" : "bg-secondary text-ink")}>
                  {m.role === "assistant" && <p className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Revised prompt</p>}
                  {m.content}
                </div>
              </motion.div>
            ))}
            {busy && (
              <div className="flex justify-start">
                <div className="flex gap-1 rounded-2xl bg-secondary px-4 py-3">
                  {[0, 1, 2].map((i) => <span key={i} className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" style={{ animationDelay: `${i * 0.15}s` }} />)}
                </div>
              </div>
            )}
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex items-center gap-2 border-t border-border p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe a change…"
              className="flex-1 rounded-full bg-secondary px-4 py-2.5 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ink/20"
            />
            <button type="submit" disabled={!input.trim() || busy} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink text-white disabled:opacity-40">
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </AppLayout>
  );
}