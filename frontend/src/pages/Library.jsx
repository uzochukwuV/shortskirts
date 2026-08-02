const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Library as LibraryIcon, Clapperboard, Search, ArrowUpRight } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import VideoCard from "@/components/VideoCard";
import EmptyState from "@/components/EmptyState";
import Chip from "@/components/Chip";

import { CATEGORIES } from "@/lib/video";

export default function Library() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    db.entities.Video.list("-created_date", 100)
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

  const filtered = videos.filter(
    (v) => (category === "all" || v.category === category) && (!query || v.prompt.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <AppLayout>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-bold tracking-tight sm:text-2xl">Library</h1>
          <p className="text-sm text-muted-foreground">{videos.length} {videos.length === 1 ? "video" : "videos"}</p>
        </div>
        <Link to="/studio" className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white">
          <Clapperboard className="h-4 w-4" /> New
        </Link>
      </div>

      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex flex-1 items-center gap-2 rounded-xl border border-border bg-card px-3 py-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search your videos…" className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground" />
        </div>
      </div>

      <div className="no-scrollbar -mx-4 mb-5 flex gap-2 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        {CATEGORIES.map((c) => (
          <Chip key={c.id} active={category === c.id} onClick={() => setCategory(c.id)} className="whitespace-nowrap">{c.label}</Chip>
        ))}
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="shimmer aspect-video rounded-xl" />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon={LibraryIcon} title="No videos here" description="Create your first cinematic clip in the Studio." action={<Link to="/studio" className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white">Open Studio <ArrowUpRight className="h-4 w-4" /></Link>} />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {filtered.map((v) => <VideoCard key={v.id} video={v} showStatus />)}
        </div>
      )}
    </AppLayout>
  );
}