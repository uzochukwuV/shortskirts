import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Zap, Plus, ArrowRight, Loader2, Film, Clock, CheckCircle2,
  AlertCircle, RefreshCw, LogOut, ChevronRight, Sparkles, Play
} from 'lucide-react';
import { storyService } from '@/services/storyService';
import { useAuth } from '@/lib/AuthContext';
import { formatDistanceToNow } from 'date-fns';

const STATUS_CONFIG = {
  draft:              { label: 'Draft',       color: 'text-white/40',   bg: 'bg-white/5',        icon: Clock },
  approved:           { label: 'Approved',    color: 'text-blue-300',   bg: 'bg-blue-500/10',    icon: CheckCircle2 },
  generating:         { label: 'Generating',  color: 'text-yellow-300', bg: 'bg-yellow-500/10',  icon: RefreshCw },
  checkpoint_review:  { label: 'Review',      color: 'text-purple-300', bg: 'bg-purple-500/10',  icon: CheckCircle2 },
  completed:          { label: 'Done',        color: 'text-emerald-300',bg: 'bg-emerald-500/10', icon: CheckCircle2 },
  failed:             { label: 'Failed',      color: 'text-red-300',    bg: 'bg-red-500/10',     icon: AlertCircle },
};

const EXAMPLE_PROMPTS = [
  'A detective in neo-Tokyo uncovers a conspiracy hidden beneath the city\'s neon lights.',
  'Two rival street artists fall in love while competing for the same wall in downtown LA.',
  'A retired astronaut receives a distress signal from the Mars colony she helped build.',
  'A chef discovers her grandmother\'s lost recipes hold the key to a family secret.',
];

function StoryCard({ story, onClick }) {
  const status = STATUS_CONFIG[story.status] || STATUS_CONFIG.draft;
  const StatusIcon = status.icon;
  const isGenerating = story.status === 'generating';
  const hasMedia = story.episode_plan?.episodes?.some(ep =>
    ep?.scenes?.some(sc => sc?.clip_url || sc?.image_url)
  );

  const thumbnail = story.episode_plan?.episodes?.[0]?.scenes?.[0]?.image_url || null;

  return (
    <button
      onClick={onClick}
      className="group text-left bg-[#141414] border border-white/8 rounded-2xl overflow-hidden hover:border-white/20 hover:bg-[#1a1a1a] transition-all duration-200 active:scale-[0.98]"
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-black/40 relative overflow-hidden">
        {thumbnail ? (
          <img src={thumbnail} alt={story.title} className="w-full h-full object-cover" />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
              <Film size={20} className="text-white/20" />
            </div>
          </div>
        )}
        {/* Generating overlay */}
        {isGenerating && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
            <div className="flex items-center gap-2 text-yellow-300 text-xs">
              <Loader2 size={14} className="animate-spin" />
              Generating…
            </div>
          </div>
        )}
        {/* Play overlay for completed */}
        {story.status === 'completed' && (
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
            <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur flex items-center justify-center">
              <Play size={16} className="text-white ml-0.5" />
            </div>
          </div>
        )}
        {/* Status badge */}
        <div className={`absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium ${status.color} ${status.bg} backdrop-blur`}>
          <StatusIcon size={10} className={isGenerating ? 'animate-spin' : ''} />
          {status.label}
        </div>
      </div>
      {/* Info */}
      <div className="p-3">
        <p className="text-sm text-white font-medium truncate mb-1">{story.title}</p>
        <div className="flex items-center justify-between">
          <span className="text-xs text-white/35">
            {story.created_at ? formatDistanceToNow(new Date(story.created_at), { addSuffix: true }) : ''}
          </span>
          <div className="flex items-center gap-1 text-xs text-white/35">
            <Film size={10} />
            {story.num_scenes || 0} scenes
          </div>
        </div>
      </div>
    </button>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [prompt, setPrompt] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [stories, setStories] = useState([]);
  const [isLoadingStories, setIsLoadingStories] = useState(true);
  const [storiesError, setStoriesError] = useState('');

  const loadStories = useCallback(async () => {
    try {
      setIsLoadingStories(true);
      setStoriesError('');
      const data = await storyService.list();
      setStories(Array.isArray(data) ? data : []);
    } catch (err) {
      setStoriesError(err?.message || 'Could not load projects.');
    } finally {
      setIsLoadingStories(false);
    }
  }, []);

  useEffect(() => {
    loadStories();
    // Poll for status updates on active generations
    const interval = setInterval(() => {
      const hasActive = stories.some(s => s.status === 'generating' || s.status === 'checkpoint_review');
      if (hasActive) loadStories();
    }, 8000);
    return () => clearInterval(interval);
  }, [loadStories, stories.length]);

  const handleCreate = async () => {
    const trimmed = prompt.trim();
    if (!trimmed || isCreating) return;
    setIsCreating(true);
    setCreateError('');
    try {
      const story = await storyService.create({
        title: trimmed.length > 56 ? `${trimmed.slice(0, 53)}…` : trimmed,
        prompt: trimmed,
        workflow_type: 'creator_series',
        requested_media_kind: 'video',
        frame_ratio: '16:9',
        requested_video_ratio: '16:9',
        num_episodes: 1,
        num_scenes: 3,
        genre: '',
        style: '',
      });
      if (!story?.id) throw new Error('Story created without an id.');
      navigate(`/workspace/${story.id}`);
    } catch (err) {
      setCreateError(err?.message || 'Could not start production.');
      setIsCreating(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCreate();
    }
  };

  const initials = user?.email ? user.email[0].toUpperCase() : 'U';

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      {/* ── Top nav ── */}
      <header className="sticky top-0 z-40 bg-[#0a0a0a]/95 backdrop-blur-xl border-b border-white/5">
        <nav className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-[#dfff1e] rounded-md flex items-center justify-center flex-shrink-0">
              <span className="text-black text-[10px] font-black">DY</span>
            </div>
            <span className="text-sm font-bold tracking-tight">Dysentry</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-white/50 text-xs">
              <Zap size={12} className="text-[#dfff1e]" />
              <span>AI Credits</span>
            </div>
            <div className="w-px h-4 bg-white/10" />
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-[#dfff1e]/20 border border-[#dfff1e]/30 flex items-center justify-center text-[#dfff1e] text-xs font-bold">
                {initials}
              </div>
              <span className="hidden sm:block text-xs text-white/50 truncate max-w-[120px]">{user?.email}</span>
            </div>
            <button
              onClick={() => logout()}
              className="text-white/40 hover:text-white/70 transition p-1.5 rounded-lg hover:bg-white/5"
              title="Sign out"
            >
              <LogOut size={14} />
            </button>
          </div>
        </nav>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        {/* ── Hero ── */}
        <div className="mb-14">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={14} className="text-[#dfff1e]" />
            <span className="text-xs text-[#dfff1e] font-medium uppercase tracking-widest">AI Video Production</span>
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight mb-3">
            What will you create today?
          </h1>
          <p className="text-white/40 text-base max-w-lg">
            Describe your story. The AI will build the outline, generate scenes, and produce your video.
          </p>
        </div>

        {/* ── Prompt input ── */}
        <div className="max-w-3xl mb-6">
          <div className="bg-[#141414] border border-white/10 rounded-2xl p-4 focus-within:border-[#dfff1e]/40 transition-colors">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your video story…"
              rows={3}
              disabled={isCreating}
              className="w-full bg-transparent text-white text-sm placeholder:text-white/25 focus:outline-none resize-none leading-relaxed"
            />
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] text-white/30">Try:</span>
                {EXAMPLE_PROMPTS.slice(0, 2).map((p) => (
                  <button
                    key={p.slice(0, 20)}
                    onClick={() => setPrompt(p)}
                    className="text-[11px] text-white/40 hover:text-white/70 bg-white/5 hover:bg-white/10 rounded-full px-2 py-1 transition truncate max-w-[180px]"
                  >
                    {p.slice(0, 40)}…
                  </button>
                ))}
              </div>
              <button
                onClick={handleCreate}
                disabled={isCreating || !prompt.trim()}
                className="ml-2 flex items-center gap-2 px-4 py-2 rounded-xl bg-[#dfff1e] text-black text-sm font-semibold hover:bg-[#c9e619] transition disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
              >
                {isCreating ? (
                  <><Loader2 size={15} className="animate-spin" /> Creating…</>
                ) : (
                  <><Plus size={15} /> Create</>
                )}
              </button>
            </div>
          </div>
          {createError && (
            <p className="mt-2 text-xs text-red-300 flex items-center gap-1.5">
              <AlertCircle size={12} /> {createError}
            </p>
          )}
        </div>

        {/* ── Projects ── */}
        <section>
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold">Your Projects</h2>
            <button
              onClick={loadStories}
              className="text-white/40 hover:text-white/70 transition p-1.5 rounded-lg hover:bg-white/5"
              title="Refresh"
            >
              <RefreshCw size={14} />
            </button>
          </div>

          {isLoadingStories ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-[#141414] border border-white/8 rounded-2xl overflow-hidden animate-pulse">
                  <div className="aspect-video bg-white/5" />
                  <div className="p-3 space-y-2">
                    <div className="h-3 bg-white/5 rounded w-3/4" />
                    <div className="h-2 bg-white/5 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : storiesError ? (
            <div className="text-center py-10">
              <AlertCircle size={24} className="text-red-400 mx-auto mb-2" />
              <p className="text-sm text-white/50 mb-3">{storiesError}</p>
              <button onClick={loadStories} className="text-xs text-[#dfff1e] hover:underline">Retry</button>
            </div>
          ) : stories.length === 0 ? (
            <div className="text-center py-16 border border-dashed border-white/10 rounded-2xl">
              <Film size={32} className="text-white/15 mx-auto mb-3" />
              <p className="text-white/40 text-sm mb-1">No projects yet</p>
              <p className="text-white/25 text-xs">Describe a story above to get started</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {stories.map((story) => (
                <StoryCard
                  key={story.id}
                  story={story}
                  onClick={() => navigate(`/workspace/${story.id}`)}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
