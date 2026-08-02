const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Search, Sparkles, ArrowUpRight, Clapperboard, Flame, Clock } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import VideoCard from "@/components/VideoCard";
import EmptyState from "@/components/EmptyState";
import Chip from "@/components/Chip";

import { CATEGORIES, PROMPT_SUGGESTIONS } from "@/lib/video";

export default function Home() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    db.entities.Video.list("-created_date", 50)
      .then((data) => setVideos(data || []))
      .finally(() => setLoading(false));

    const unsub = db.entities.Video.subscribe((event) => {
      setVideos((prev) => {
        if (event.type === "create") return [event.data, ...prev];
        if (event.type === "update") return prev.map((v) => (v.id === event.data.id ? event.data : v));
        if (event.type === "delete") return prev.filter((v) => v.id !== event.id);
        return prev;
      });
    });
    return unsub;
  }, []);

  const ready = videos.filter((v) => v.status === "ready");
  const trending = [...ready].sort((a, b) => (b.likes || 0) - (a.likes || 0)).slice(0, 6);
  const filtered = ready.filter(
    (v) => (category === "all" || v.category === category) && (!query || v.prompt.toLowerCase().includes(query.toLowerCase()))
  );

  const submitPrompt = (e) => {
    e?.preventDefault();
    const prompt = query.trim();
    if (prompt.length < 3) return;
    navigate("/studio", { state: { prompt } });
  };

  return (
    <AppLayout>
      {/* Greeting */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <p className="text-sm text-muted-foreground">Good to see you</p>
        <h1 className="mt-0.5 font-display text-2xl font-bold tracking-tight sm:text-3xl">Create something cinematic today.</h1>
      </motion.div>

      {/* Search-to-prompt */}
      <form onSubmit={submitPrompt} className="relative mb-8">
        <div className="flex items-center gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm focus-within:border-ink/40">
          <Search className="ml-2 h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe a video to create…"
            className="flex-1 bg-transparent py-2 text-sm outline-none placeholder:text-muted-foreground"
          />
          <button type="submit" className="inline-flex items-center gap-1.5 rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={query.trim().length < 3}>
            <Sparkles className="h-3.5 w-3.5" /> Generate
          </button>
        </div>
        <div className="mt-2.5 flex flex-wrap gap-2">
          {PROMPT_SUGGESTIONS.slice(0, 3).map((s) => (
            <button key={s} type="button" onClick={() => setQuery(s)} className="rounded-full border border-border bg-card px-3 py-1 text-[11px] text-muted-foreground hover:border-ink/40 hover:text-ink">
              {s}
            </button>
          ))}
        </div>
      </form>

      {/* Quick create CTA */}
      <Link to="/studio" className="mb-8 flex items-center justify-between rounded-2xl border border-border bg-ink p-5 text-white transition-transform hover:scale-[1.01]">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10"><Clapperboard className="h-5 w-5" /></span>
          <div>
            <p className="text-sm font-semibold">Open the Studio</p>
            <p className="text-xs text-white/70">Full control over every setting</p>
          </div>
        </div>
        <ArrowUpRight className="h-5 w-5" />
      </Link>

      {/* Categories */}
      <div className="no-scrollbar -mx-4 mb-5 flex gap-2 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        {CATEGORIES.map((c) => (
          <Chip key={c.id} active={category === c.id} onClick={() => setCategory(c.id)} className="whitespace-nowrap">
            {c.label}
          </Chip>
        ))}
      </div>

      {/* Trending */}
      {trending.length > 0 && (
        <section className="mb-10">
          <div className="mb-3 flex items-center gap-2">
            <Flame className="h-4 w-4 text-ink" />
            <h2 className="text-sm font-semibold">Trending</h2>
          </div>
          <div className="no-scrollbar -mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0 lg:grid lg:grid-cols-3 lg:overflow-visible">
            {trending.map((v) => (
              <div key={v.id} className="w-[78%] shrink-0 snap-start sm:w-[45%] lg:w-auto">
                <VideoCard video={v} />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Recent */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Clock className="h-4 w-4 text-ink" />
          <h2 className="text-sm font-semibold">Recent creations</h2>
        </div>
        {loading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="shimmer aspect-video rounded-xl" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={Clapperboard} title="No videos yet" description="Head to the Studio to create your first cinematic clip." action={<Link to="/studio" className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white">Open Studio <ArrowUpRight className="h-4 w-4" /></Link>} />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {filtered.map((v) => <VideoCard key={v.id} video={v} />)}
          </div>
        )}
      </section>
    </AppLayout>
  );
}