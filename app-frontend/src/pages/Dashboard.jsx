import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, Home as HomeIcon, Folder, ChevronDown, ArrowRight, Loader2 } from "lucide-react";
import { storyService } from "@/services/storyService";
import VideoCard from "@/components/VideoCard";

const aiFilmVideos = [
  { title: "Upgrade Service", author: "Yibo", image_url: "https://res.papir.cc/buzzy-assets/G5o9gnSKGhY_Vn8XXsk3m_1782121168629_i1.avif" },
  { title: "Backroom Escape", author: "Neo", image_url: "https://res.creatiai.ai/web/creatiai/tag1-backroom_poster.avif" },
  { title: "The Last Key", author: "Roman", image_url: "https://res.creatiai.ai/web/creatiai/tag1-the-last-key.avif" },
  { title: "Before Rome Sunset", author: "El", image_url: "https://res.papir.cc/buzzy-assets/9buzS7r3tWU_SKNWBKq8K_1782121170648_i0.avif" },
];

const quickTags = ["+ New Project", "AI Film", "Trend Inspire", "Branding Ads", "AI Animations", "UGC Ads", "Logo & Branding", "All Skills"];

export default function Dashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("Create a video");
  const [prompt, setPrompt] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || isCreating) return;
    setIsCreating(true);
    setError("");
    try {
      const story = await storyService.create({
        title: trimmedPrompt.length > 56 ? `${trimmedPrompt.slice(0, 53)}...` : trimmedPrompt,
        prompt: trimmedPrompt,
        workflow_type: activeTab === "AI edit" ? "social_short" : "creator_series",
        requested_media_kind: "video",
        frame_ratio: "16:9",
        requested_video_ratio: "16:9",
        num_episodes: 1,
        num_scenes: 3,
      });
      if (!story?.id) throw new Error("The story was created without an id.");
      navigate(`/workspace/${story.id}`);
    } catch (err) {
      setError(err?.message || "Could not start the production.");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Top nav */}
      <header className="sticky top-0 z-40 bg-[#0a0a0a]/90 backdrop-blur-xl border-b border-white/5">
        <nav className="max-w-[1400px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-2">
          <span className="text-base sm:text-lg font-bold tracking-tighter text-white flex-shrink-0">SONICVISION</span>
          <div className="hidden md:flex items-center gap-8 flex-shrink-0">
            <button className="text-white/60 hover:text-white text-sm">Models</button>
            <button className="text-white/60 hover:text-white text-sm">Skills</button>
            <button className="text-white/60 hover:text-white text-sm">Blogs</button>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            <button className="hidden sm:block bg-white/10 text-white text-xs px-3 py-1.5 rounded-full hover:bg-white/20 transition">Buy Credits</button>
            <div className="flex items-center gap-1 text-white/60 text-xs">
              <Zap size={14} className="text-[#dfff1e]" /> 0
            </div>
            <button className="bg-[#dfff1e] text-black text-xs font-semibold px-3 py-1.5 rounded-full hover:bg-[#c5e01a] transition">Upgrade</button>
            <button className="text-white/60 hover:text-white"><HomeIcon size={16} /></button>
            <button className="text-white/60 hover:text-white hidden sm:block"><Folder size={16} /></button>
            <div className="w-7 h-7 rounded-full bg-green-500/80 flex items-center justify-center text-white text-xs font-medium flex-shrink-0">V</div>
          </div>
        </nav>
      </header>

      {/* Hero section */}
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-10 sm:py-16 lg:py-20">
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold text-white text-center mb-8 tracking-tight">
          Pro Video, Made Easy
        </h1>

        {/* Tab toggle */}
        <div className="flex justify-center mb-8">
          <div className="bg-white/5 rounded-full p-1 flex">
            {["Create a video", "AI edit"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 sm:px-5 py-2 rounded-full text-sm font-medium transition-all ${
                  activeTab === tab ? "bg-[#dfff1e] text-black" : "text-white/50 hover:text-white"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Prompt input */}
        <div className="max-w-3xl mx-auto">
          <div className="bg-[#141414] border border-white/10 rounded-2xl p-4 focus-within:border-[#dfff1e]/30 transition">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Help me craft a video story about :"
              rows={3}
              className="w-full bg-transparent text-white text-sm placeholder:text-white/30 focus:outline-none resize-none"
            />
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              <span className="border border-[#dfff1e] text-[#dfff1e] text-xs px-3 py-1 rounded-full flex items-center gap-1">
                Agent Mode <ChevronDown size={10} />
              </span>
              <span className="border border-white/20 text-white/60 text-xs px-3 py-1 rounded-full">AI Film</span>
              <button
                onClick={handleSubmit}
                disabled={isCreating || !prompt.trim()}
                className="ml-auto w-10 h-10 rounded-full bg-[#dfff1e] flex items-center justify-center hover:bg-[#c5e01a] transition active:scale-90 flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isCreating ? <Loader2 size={18} className="text-black animate-spin" /> : <ArrowRight size={18} className="text-black" />}
              </button>
            </div>
          </div>

          {error && <p className="mt-3 text-xs text-red-300">{error}</p>}

          {/* Quick action tags */}
          <div className="flex flex-wrap gap-2 mt-6 justify-center">
            {quickTags.map((tag) => (
              <button
                key={tag}
                onClick={tag === "+ New Project" ? () => document.querySelector("textarea")?.focus() : undefined}
                className="bg-white/5 text-white/60 text-xs sm:text-sm px-3 sm:px-4 py-1.5 rounded-full hover:bg-white/10 hover:text-white transition border border-white/5"
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* AI Film section */}
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-20">
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-6">AI Film</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {aiFilmVideos.map((v) => (
            <VideoCard key={v.title} {...v} />
          ))}
        </div>
      </div>

      {/* Floating chat button */}
      <button className="fixed bottom-6 right-6 w-12 h-12 rounded-full bg-[#dfff1e] flex items-center justify-center shadow-lg hover:scale-110 transition-transform z-50">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M12 3C6.5 3 2 6.5 2 11C2 13 3 14.8 4.5 16L4 19L7.5 17.5C9 18 10.5 18.3 12 18.3C17.5 18.3 22 14.8 22 10.5C22 6.2 17.5 3 12 3Z" fill="black" />
        </svg>
      </button>
    </div>
  );
}