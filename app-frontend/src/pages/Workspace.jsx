import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, Bot, CheckCircle2, ChevronRight, Clapperboard, Film,
  ImageIcon, Loader2, Play, Plus, RefreshCw, Send, Settings2,
  Sparkles, Wrench, X, Zap, Lock, Unlock, AlertCircle, Users,
  ChevronDown, ChevronUp
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { agentService } from '@/services/agentService';
import { storyService } from '@/services/storyService';
import { episodeService } from '@/services/episodeService';
import { characterService } from '@/services/characterService';
import { jobService } from '@/services/jobService';
import { sceneService } from '@/services/sceneService';

// ─── Status helpers ──────────────────────────────────────────────────────────

const STATUS_DOT = {
  pending:   'bg-white/20',
  running:   'bg-yellow-400 animate-pulse',
  completed: 'bg-emerald-400',
  failed:    'bg-red-400',
  approved:  'bg-blue-400',
  rejected:  'bg-red-400',
};

const STORY_STATUS_BADGE = {
  draft:             { label: 'Draft',       cls: 'text-white/40 bg-white/5' },
  approved:          { label: 'Approved',    cls: 'text-blue-300 bg-blue-500/10' },
  generating:        { label: 'Generating',  cls: 'text-yellow-300 bg-yellow-500/10' },
  checkpoint_review: { label: 'Review',      cls: 'text-purple-300 bg-purple-500/10' },
  completed:         { label: 'Done',        cls: 'text-emerald-300 bg-emerald-500/10' },
  failed:            { label: 'Failed',      cls: 'text-red-300 bg-red-500/10' },
};

// ─── Scene Thumbnail ─────────────────────────────────────────────────────────

function SceneThumbnail({ scene, selected, onClick }) {
  const isActive = selected;
  const mediaUrl = scene.clip_url || scene.image_url;
  const dotCls = STATUS_DOT[scene.status] || 'bg-white/20';

  return (
    <button
      onClick={onClick}
      className={`relative group flex-shrink-0 w-full text-left rounded-xl overflow-hidden border transition-all ${
        isActive
          ? 'border-[#dfff1e] ring-1 ring-[#dfff1e]/30'
          : 'border-white/8 hover:border-white/25'
      }`}
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-black/40 relative overflow-hidden">
        {mediaUrl ? (
          scene.clip_url ? (
            <video
              src={scene.clip_url}
              className="w-full h-full object-cover"
              muted
              preload="metadata"
            />
          ) : (
            <img src={scene.image_url} alt={scene.title} className="w-full h-full object-cover" />
          )
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <Film size={16} className="text-white/15" />
          </div>
        )}
        {scene.status === 'running' && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <Loader2 size={14} className="text-[#dfff1e] animate-spin" />
          </div>
        )}
        {/* Scene number badge */}
        <span className="absolute top-1.5 left-1.5 text-[10px] bg-black/70 text-white/60 rounded px-1.5 py-0.5">
          {scene.scene_number}
        </span>
      </div>
      {/* Label row */}
      <div className={`px-2 py-1.5 flex items-center justify-between gap-1 ${isActive ? 'bg-[#dfff1e]/5' : 'bg-[#141414]'}`}>
        <span className="text-[11px] text-white/60 truncate flex-1">{scene.title || `Scene ${scene.scene_number}`}</span>
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotCls}`} />
      </div>
    </button>
  );
}

// ─── Scene Viewer ─────────────────────────────────────────────────────────────

function SceneViewer({ scene, story, onGenerate, onApprove, onRegenerate, isGenerating }) {
  const [videoError, setVideoError] = useState(false);
  const mediaUrl = scene?.clip_url || scene?.image_url;
  const canGenerate = story?.status === 'approved' || story?.status === 'draft';
  const canApprove  = scene?.status === 'completed' && scene?.approval_status !== 'approved';

  useEffect(() => {
    setVideoError(false);
  }, [scene?.id, scene?.clip_url, scene?.image_url]);

  if (!scene) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.04)_1px,_transparent_1px)] [background-size:28px_28px]">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/8 flex items-center justify-center mx-auto mb-4">
            <Clapperboard size={24} className="text-white/20" />
          </div>
          <p className="text-white/30 text-sm">No scene selected</p>
          <p className="text-white/20 text-xs mt-1">Select a scene from the sidebar</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Media viewer */}
      <div className="flex-1 min-h-0 relative flex items-center justify-center bg-black/60 overflow-hidden">
        {mediaUrl && !videoError ? (
          scene.clip_url ? (
            <video
              key={scene.clip_url}
              src={scene.clip_url}
              controls
              className="max-w-full max-h-full object-contain"
              onError={() => setVideoError(true)}
            />
          ) : (
            <img
              src={scene.image_url}
              alt={scene.title}
              className="max-w-full max-h-full object-contain"
              onError={() => setVideoError(true)}
            />
          )
        ) : scene.status === 'running' ? (
          <div className="flex flex-col items-center gap-3 text-yellow-300">
            <Loader2 size={32} className="animate-spin" />
            <p className="text-sm">Generating scene…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-white/20">
            <div className="w-20 h-20 rounded-2xl bg-white/5 border border-white/8 flex items-center justify-center">
              <ImageIcon size={28} className="text-white/15" />
            </div>
            <p className="text-sm text-white/30">No media yet</p>
            {canGenerate && (
              <button
                onClick={onGenerate}
                disabled={isGenerating}
                className="mt-2 px-4 py-2 rounded-xl bg-[#dfff1e] text-black text-sm font-semibold hover:bg-[#c9e619] transition disabled:opacity-40"
              >
                {isGenerating ? <Loader2 size={14} className="animate-spin inline mr-2" /> : null}
                Generate Now
              </button>
            )}
          </div>
        )}
      </div>

      {/* Scene metadata strip */}
      <div className="bg-[#111111] border-t border-white/5 px-4 py-3 flex items-center justify-between gap-4 flex-shrink-0">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-white font-medium text-sm truncate">{scene.title || `Scene ${scene.scene_number}`}</span>
            {scene.locked && <Lock size={11} className="text-white/40 flex-shrink-0" />}
          </div>
          <p className="text-white/40 text-xs truncate">{scene.description || scene.visual_prompt || '—'}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {scene.status === 'completed' && !scene.locked && (
            <button
              onClick={onRegenerate}
              disabled={isGenerating}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 hover:text-white text-xs transition disabled:opacity-40"
            >
              <RefreshCw size={12} /> Redo
            </button>
          )}
          {canApprove && (
            <button
              onClick={onApprove}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 text-xs transition"
            >
              <CheckCircle2 size={12} /> Approve
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Chat Panel ───────────────────────────────────────────────────────────────

function ChatPanel({ messages, draft, setDraft, onSend, isSending, canChat, status, error, messagesEndRef }) {
  const statusBadge = STORY_STATUS_BADGE[status] || STORY_STATUS_BADGE.draft;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-white/30 mb-0.5">Production Assistant</p>
            <h3 className="text-sm font-semibold flex items-center gap-1.5">
              <Bot size={14} className="text-[#dfff1e]" /> Dysentry AI
            </h3>
          </div>
          <span className={`text-[10px] uppercase tracking-wider rounded-full px-2 py-1 font-medium ${statusBadge.cls}`}>
            {statusBadge.label}
          </span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 space-y-3">
        <div className="flex gap-2 text-xs text-white/35 items-start">
          <Bot size={12} className="text-[#dfff1e] mt-0.5 flex-shrink-0" />
          <span>I can shape the story, manage characters, and start generation when you're ready.</span>
        </div>

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[92%] rounded-2xl px-3 py-2.5 text-sm ${
                msg.role === 'user'
                  ? 'bg-[#dfff1e] text-black rounded-br-md'
                  : msg.error
                  ? 'bg-red-500/10 text-red-200 border border-red-500/20 rounded-bl-md'
                  : 'bg-white/5 text-white/80 border border-white/5 rounded-bl-md'
              }`}
            >
              {msg.role === 'assistant' && !msg.error ? (
                <ReactMarkdown
                  className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0"
                  components={{ p: ({ children }) => <p className="whitespace-pre-wrap leading-relaxed">{children}</p> }}
                >
                  {msg.content}
                </ReactMarkdown>
              ) : (
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              )}
              {/* Tool calls */}
              {msg.actions?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-white/10 space-y-1">
                  {msg.actions.map((action, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-[11px] text-white/50">
                      <Wrench size={10} className="text-[#dfff1e]" />
                      <span className="font-mono">{action.tool}</span>
                      {action.error
                        ? <X size={10} className="text-red-300 ml-auto" />
                        : <CheckCircle2 size={10} className="text-emerald-300 ml-auto" />
                      }
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isSending && (
          <div className="flex items-center gap-2 text-xs text-white/40">
            <Loader2 size={12} className="animate-spin text-[#dfff1e]" />
            <span>Thinking…</span>
          </div>
        )}
        {error && <p className="text-xs text-red-300 px-1">{error}</p>}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={onSend} className="p-3 border-t border-white/5 flex-shrink-0">
        <div className="relative">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSend(e); }
            }}
            disabled={!canChat}
            rows={2}
            placeholder={canChat ? 'Ask me to shape scenes, add characters, generate…' : 'Open a story to start chatting…'}
            className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 pr-10 text-sm text-white placeholder:text-white/25 outline-none focus:border-[#dfff1e]/40 disabled:opacity-40 transition-colors"
          />
          <button
            type="submit"
            disabled={!canChat || !draft.trim()}
            className="absolute right-2 bottom-2 w-7 h-7 rounded-lg bg-[#dfff1e] text-black flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#c9e619] transition"
          >
            <Send size={13} />
          </button>
        </div>
        <p className="mt-1.5 text-[10px] text-white/25 text-right">Enter to send · Shift+Enter for newline</p>
      </form>
    </div>
  );
}

// ─── Assets Panel ──────────────────────────────────────────────────────────────

function AssetsPanel({ scenes, characters, storyId, refreshKey }) {
  const [tab, setTab] = useState('scenes');
  const [libraryAssets, setLibraryAssets] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    let cancelled = false;
    if (!storyId) return undefined;

    setIsLoading(true);
    setLoadError('');
    agentService.storyAssets(storyId)
      .then((response) => {
        if (!cancelled) {
          setLibraryAssets(Array.isArray(response) ? response : response?.assets || []);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setLoadError(error?.message || 'Could not load generated assets.');
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => { cancelled = true; };
  }, [refreshKey, storyId]);

  const referenceAssets = [
    ...characters.flatMap((character) =>
      (Array.isArray(character.ref_image_urls) ? character.ref_image_urls : []).map((url, index) => ({
        id: `${character.id}-reference-${index}`,
        url,
        name: `${character.name || 'Character'} reference ${index + 1}`,
        detail: character.role || 'Character reference',
        type: 'image',
      })),
    ),
    ...scenes
      .filter((scene) => scene.exit_frame_url)
      .map((scene) => ({
        id: `${scene.id}-exit-frame`,
        url: scene.exit_frame_url,
        name: `${scene.title || `Scene ${scene.scene_number}`} exit frame`,
        detail: 'Continuity reference',
        type: 'image',
      })),
  ];

  const generatedAssets = libraryAssets
    .map((asset, index) => {
      const url = asset.url || asset.storage_url || asset.public_url || asset.file_url;
      const type = asset.asset_type || asset.media_type || asset.mime_type || '';
      return {
        id: asset.id || asset.storage_key || `asset-${index}`,
        url,
        name: asset.name || asset.title || asset.storage_key?.split('/').pop() || 'Generated asset',
        detail: asset.entity_type || asset.asset_type || 'Generated',
        type: type.includes('video') ? 'video' : 'image',
      };
    })
    .filter((asset) => asset.url);

  const renderAsset = (asset, compact = false) => (
    <div
      key={asset.id}
      className={`rounded-xl bg-white/[0.03] border border-white/5 overflow-hidden ${
        compact ? 'flex items-center gap-3 p-2' : ''
      }`}
    >
      <div className={compact ? 'w-16 h-10 flex-shrink-0 bg-black/40 overflow-hidden' : 'aspect-video bg-black/40 overflow-hidden'}>
        {asset.type === 'video' ? (
          <video src={asset.url} muted preload="metadata" className="w-full h-full object-cover" />
        ) : (
          <img src={asset.url} alt={asset.name} loading="lazy" className="w-full h-full object-cover" />
        )}
      </div>
      <div className={compact ? 'min-w-0' : 'p-2'}>
        <p className="text-xs text-white/70 truncate">{asset.name}</p>
        <p className="text-[10px] text-white/30 truncate">{asset.detail}</p>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-3 pb-0 border-b border-white/5 flex-shrink-0">
        <div className="flex gap-1 mb-0">
          {['scenes', 'references', 'library'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-2 text-xs font-medium capitalize rounded-t-lg transition ${
                tab === t ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'
              }`}
            >
              {t} ({t === 'scenes' ? scenes.length : t === 'references' ? referenceAssets.length : generatedAssets.length})
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2">
        {tab === 'scenes' && (
          scenes.length === 0 ? (
            <div className="text-center py-8 text-white/30 text-xs">No scenes yet</div>
          ) : (
            scenes.map((scene) => {
              const mediaUrl = scene.clip_url || scene.image_url;
              return (
                <div key={scene.id} className="flex items-center gap-3 p-2 rounded-xl bg-white/3 border border-white/5 hover:border-white/12 transition">
                  <div className="w-16 h-9 rounded-md bg-black/40 flex-shrink-0 overflow-hidden">
                    {mediaUrl ? (
                      scene.clip_url ? (
                        <video src={scene.clip_url} muted preload="metadata" className="w-full h-full object-cover" />
                      ) : (
                        <img src={mediaUrl} alt="" loading="lazy" className="w-full h-full object-cover" />
                      )
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Film size={10} className="text-white/15" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-white/70 truncate">{scene.title || `Scene ${scene.scene_number}`}</p>
                    <p className="text-[10px] text-white/30 truncate">{scene.mood || scene.location || '—'}</p>
                  </div>
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${STATUS_DOT[scene.status] || 'bg-white/20'}`} />
                </div>
              );
            })
          )
        )}

        {tab === 'references' && (
          referenceAssets.length === 0 ? (
            <div className="text-center py-8 text-white/30 text-xs">No reference images yet</div>
          ) : (
            <div className="grid grid-cols-2 gap-2">{referenceAssets.map((asset) => renderAsset(asset))}</div>
          )
        )}

        {tab === 'library' && (
          isLoading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-xs text-white/40">
              <Loader2 size={13} className="animate-spin text-[#dfff1e]" /> Loading assets…
            </div>
          ) : loadError ? (
            <div className="text-center py-8 text-xs text-red-300/70">{loadError}</div>
          ) : generatedAssets.length === 0 ? (
            <div className="text-center py-8 text-white/30 text-xs">Generated assets will appear here</div>
          ) : (
            <div className="space-y-2">{generatedAssets.map((asset) => renderAsset(asset, true))}</div>
          )
        )}
      </div>
    </div>
  );
}

// ─── Settings Panel ───────────────────────────────────────────────────────────

function SettingsPanel({ story, onApproveOutline, onGenerate, isWorking }) {
  const canApprove  = story?.status === 'draft';
  const canGenerate = story?.status === 'approved';
  const isActive    = story?.status === 'generating' || story?.status === 'checkpoint_review';

  return (
    <div className="flex flex-col h-full p-4 space-y-4 overflow-y-auto">
      <div>
        <p className="text-[10px] uppercase tracking-widest text-white/30 mb-3">Production</p>

        {/* Status info */}
        <div className="bg-white/3 border border-white/8 rounded-xl p-3 mb-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/50">Status</span>
            <span className={`text-xs font-medium ${STORY_STATUS_BADGE[story?.status]?.cls || ''}`}>
              {STORY_STATUS_BADGE[story?.status]?.label || 'Unknown'}
            </span>
          </div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-white/50">Scenes</span>
            <span className="text-xs text-white/70">{story?.num_scenes || 0}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/50">Episodes</span>
            <span className="text-xs text-white/70">{story?.num_episodes || 0}</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="space-y-2">
          {canApprove && (
            <button
              onClick={onApproveOutline}
              disabled={isWorking}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 text-sm font-medium transition disabled:opacity-40"
            >
              <CheckCircle2 size={15} /> Approve Outline
            </button>
          )}
          {canGenerate && (
            <button
              onClick={onGenerate}
              disabled={isWorking}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-[#dfff1e] hover:bg-[#c9e619] text-black text-sm font-semibold transition disabled:opacity-40"
            >
              {isWorking ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
              Generate All Scenes
            </button>
          )}
          {isActive && (
            <div className="flex items-center justify-center gap-2 py-2.5 text-yellow-300 text-sm">
              <Loader2 size={14} className="animate-spin" />
              {story?.status === 'generating' ? 'Generating…' : 'Awaiting review…'}
            </div>
          )}
        </div>
      </div>

      {/* Story outline */}
      {story?.episode_plan?.synopsis && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-white/30 mb-2">Synopsis</p>
          <p className="text-xs text-white/50 leading-relaxed">{story.episode_plan.synopsis}</p>
        </div>
      )}

      {story?.episode_plan?.setting && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-white/30 mb-2">Setting</p>
          <p className="text-xs text-white/50 leading-relaxed">{story.episode_plan.setting}</p>
        </div>
      )}

      {story?.episode_plan?.themes?.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-white/30 mb-2">Themes</p>
          <div className="flex flex-wrap gap-1.5">
            {story.episode_plan.themes.map((t) => (
              <span key={t} className="text-[11px] bg-white/5 text-white/50 rounded-full px-2 py-0.5">{t}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Job Status Bar ───────────────────────────────────────────────────────────

function JobStatusBar({ job }) {
  if (!job || ['completed', 'failed', 'canceled'].includes(job.status)) return null;
  const pct = job.total_steps > 0 ? Math.round((job.progress / job.total_steps) * 100) : 0;
  return (
    <div className="bg-yellow-500/5 border-t border-yellow-500/10 px-4 py-2 flex items-center gap-3 flex-shrink-0">
      <Loader2 size={12} className="text-yellow-300 animate-spin flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-yellow-200/80 truncate">{job.current_step || 'Processing…'}</p>
        {job.total_steps > 0 && (
          <div className="mt-1 h-1 bg-white/5 rounded-full overflow-hidden">
            <div className="h-full bg-yellow-400/70 rounded-full transition-all" style={{ width: `${pct}%` }} />
          </div>
        )}
      </div>
      <span className="text-xs text-yellow-300/60 flex-shrink-0">{pct ? `${pct}%` : '…'}</span>
    </div>
  );
}

// ─── Main Workspace ───────────────────────────────────────────────────────────

const INITIAL_MESSAGE = {
  id: 'welcome',
  role: 'assistant',
  content: "Tell me what you want to make. I can shape the story, revise scenes, manage characters, and start generation when the plan is ready.",
};

const SIDE_TABS = [
  { id: 'chat',     label: 'Chat',     icon: Bot },
  { id: 'assets',   label: 'Assets',   icon: Film },
  { id: 'settings', label: 'Settings', icon: Settings2 },
];

export default function Workspace() {
  const navigate = useNavigate();
  const { storyId } = useParams();

  // Core data
  const [story,      setStory]      = useState(null);
  const [episodes,   setEpisodes]   = useState([]);
  const [scenes,     setScenes]     = useState([]);  // flat list across all episodes
  const [characters, setCharacters] = useState([]);
  const [activeJob,  setActiveJob]  = useState(null);
  const [selectedSceneId, setSelectedSceneId] = useState(null);

  // UI state
  const [activeTab,  setActiveTab]  = useState('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Chat state
  const [messages,       setMessages]       = useState([INITIAL_MESSAGE]);
  const [conversationId, setConversationId] = useState(null);
  const [draft,          setDraft]          = useState('');
  const [isSending,      setIsSending]      = useState(false);
  const [chatError,      setChatError]      = useState('');

  // Loading / error
  const [isLoading,  setIsLoading]  = useState(true);
  const [loadError,  setLoadError]  = useState('');
  const [isWorking,  setIsWorking]  = useState(false);

  const messagesEndRef = useRef(null);
  const pollRef        = useRef(null);
  const lastJobStateRef = useRef('');

  // ── Load story + episodes + scenes + characters ────────────────────────────

  const loadAll = useCallback(async (quiet = false) => {
    if (!storyId) return;
    if (!quiet) setIsLoading(true);
    setLoadError('');
    try {
      const [storyData, epData, charData] = await Promise.all([
        storyService.get(storyId),
        episodeService.listByStory(storyId).catch(() => []),
        characterService.listByStory(storyId).catch(() => []),
      ]);
      setStory(storyData);
      setEpisodes(Array.isArray(epData) ? epData : []);
      setCharacters(Array.isArray(charData) ? charData : []);

      // Flatten scenes
      const allScenes = (Array.isArray(epData) ? epData : []).flatMap(ep => ep.scenes || []);
      setScenes(allScenes);
      if (!selectedSceneId && allScenes.length > 0) {
        setSelectedSceneId(allScenes[0].id);
      }
    } catch (err) {
      setLoadError(err?.message || 'Could not load this project.');
    } finally {
      setIsLoading(false);
    }
  }, [storyId]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // ── Poll active job ────────────────────────────────────────────────────────

  useEffect(() => {
    if (!storyId) return;
    const poll = async () => {
      try {
        const jobs = await jobService.byEntity('story', storyId);
        const active = (Array.isArray(jobs) ? jobs : []).find(
          j => ['pending', 'running', 'retrying'].includes(j.status)
        );
        setActiveJob(active || null);
        const jobState = active ? `${active.id}:${active.status}` : 'idle';
        if (jobState !== lastJobStateRef.current) {
          lastJobStateRef.current = jobState;
          loadAll(true); // refresh when generation starts or reaches a terminal state
        }
      } catch {}
    };
    poll();
    pollRef.current = setInterval(poll, 5000);
    return () => clearInterval(pollRef.current);
  }, [storyId, loadAll]);

  // ── Scroll to bottom on new messages ──────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  // ── Chat ──────────────────────────────────────────────────────────────────

  const sendMessage = async (e) => {
    e?.preventDefault();
    const text = draft.trim();
    if (!text || !storyId || isSending) return;
    setDraft('');
    setChatError('');
    setMessages(prev => [...prev, { id: `u-${Date.now()}`, role: 'user', content: text }]);
    setIsSending(true);
    try {
      const res = await agentService.chat({
        message: text,
        story_id: storyId,
        conversation_id: conversationId || undefined,
        include_context: true,
      });
      if (res?.conversation_id) setConversationId(res.conversation_id);
      setMessages(prev => [...prev, {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: res?.message || 'Done.',
        actions: res?.actions || [],
      }]);
      loadAll(true);
    } catch (err) {
      setChatError(err?.message || 'Could not reach the assistant.');
      setMessages(prev => [...prev, {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'I could not complete that. Please check the connection and try again.',
        error: true,
      }]);
    } finally {
      setIsSending(false);
    }
  };

  // ── Production actions ────────────────────────────────────────────────────

  const approveOutline = async () => {
    setIsWorking(true);
    try {
      const updated = await storyService.approveOutline(storyId);
      setStory(updated);
    } catch (err) {
      setChatError(err?.message || 'Could not approve outline.');
    } finally {
      setIsWorking(false);
    }
  };

  const launchGeneration = async () => {
    setIsWorking(true);
    try {
      await storyService.launchGeneration(storyId);
      await loadAll(true);
    } catch (err) {
      setChatError(err?.message || 'Could not start generation.');
    } finally {
      setIsWorking(false);
    }
  };

  const approveScene = async () => {
    if (!selectedSceneId) return;
    try {
      const updated = await sceneService.approve(selectedSceneId);
      setScenes(prev => prev.map(s => s.id === updated.id ? updated : s));
    } catch (err) {
      setChatError(err?.message || 'Could not approve scene.');
    }
  };

  const regenerateScene = async () => {
    if (!selectedSceneId) return;
    setIsWorking(true);
    try {
      await sceneService.regenerate(selectedSceneId);
      await loadAll(true);
    } catch (err) {
      setChatError(err?.message || 'Could not regenerate scene.');
    } finally {
      setIsWorking(false);
    }
  };

  // ── Derived ───────────────────────────────────────────────────────────────

  const selectedScene = scenes.find(s => s.id === selectedSceneId) || null;
  const title = story?.title || 'New Project';
  const canChat = Boolean(storyId) && !isSending;
  const isGeneratingStory = story?.status === 'generating';

  // ── Render ────────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={24} className="text-[#dfff1e] animate-spin" />
          <span className="text-white/40 text-sm">Loading project…</span>
        </div>
      </div>
    );
  }

  if (loadError && !story) {
    return (
      <div className="h-screen bg-[#0a0a0a] flex items-center justify-center p-6">
        <div className="text-center max-w-sm">
          <AlertCircle size={28} className="text-red-400 mx-auto mb-3" />
          <p className="text-white/70 text-sm mb-4">{loadError}</p>
          <button onClick={() => navigate('/dashboard')} className="text-[#dfff1e] text-sm hover:underline">
            ← Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-[#0a0a0a] flex flex-col overflow-hidden text-white">
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-3 py-2 border-b border-white/5 bg-[#0a0a0a] z-20 flex-shrink-0 h-12">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-white/40 hover:text-white transition flex-shrink-0"
          >
            <ArrowLeft size={16} />
          </button>
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-5 h-5 bg-[#dfff1e] rounded flex-shrink-0" />
            <span className="text-sm text-white/80 font-medium truncate">{title}</span>
          </div>
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${STORY_STATUS_BADGE[story?.status]?.cls || ''}`}>
            {STORY_STATUS_BADGE[story?.status]?.label || ''}
          </span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {SIDE_TABS.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition ${
                  activeTab === tab.id
                    ? 'bg-[#dfff1e] text-black'
                    : 'text-white/50 hover:text-white bg-white/5 hover:bg-white/10'
                }`}
              >
                <Icon size={12} /> {tab.label}
              </button>
            );
          })}
        </div>
      </header>

      {/* ── Job status bar ── */}
      <JobStatusBar job={activeJob} />

      {/* ── Body ── */}
      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Scene sidebar (left) */}
        <aside
          className={`flex-shrink-0 border-r border-white/5 bg-[#0d0d0d] flex flex-col overflow-hidden transition-all duration-200 ${
            sidebarOpen ? 'w-[160px] sm:w-[180px]' : 'w-0'
          }`}
        >
          {/* Sidebar header */}
          <div className="px-3 py-2.5 border-b border-white/5 flex items-center justify-between flex-shrink-0">
            <span className="text-[10px] uppercase tracking-widest text-white/30">Scenes</span>
            <span className="text-[10px] text-white/25">{scenes.length}</span>
          </div>
          {/* Scene list */}
          <div className="flex-1 min-h-0 overflow-y-auto p-2 space-y-1.5">
            {scenes.length === 0 ? (
              <div className="text-center py-6">
                <p className="text-[11px] text-white/25">No scenes yet</p>
                <p className="text-[10px] text-white/15 mt-1">Chat to create scenes</p>
              </div>
            ) : (
              scenes.map(sc => (
                <SceneThumbnail
                  key={sc.id}
                  scene={sc}
                  selected={sc.id === selectedSceneId}
                  onClick={() => setSelectedSceneId(sc.id)}
                />
              ))
            )}
          </div>
        </aside>

        {/* Toggle sidebar */}
        <button
          onClick={() => setSidebarOpen(o => !o)}
          className="flex-shrink-0 w-4 bg-[#0d0d0d] border-r border-white/5 hover:bg-white/5 transition flex items-center justify-center text-white/20 hover:text-white/50"
        >
          {sidebarOpen ? <ChevronLeft size={12} /> : <ChevronRight size={12} />}
        </button>

        {/* Scene viewer (center) */}
        <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
          <SceneViewer
            scene={selectedScene}
            story={story}
            onGenerate={launchGeneration}
            onApprove={approveScene}
            onRegenerate={regenerateScene}
            isGenerating={isWorking || isGeneratingStory}
          />
        </main>

        {/* Right panel */}
        <aside className="w-[340px] lg:w-[380px] flex-shrink-0 border-l border-white/5 bg-[#111111] flex flex-col overflow-hidden">
          {/* Mobile tab bar */}
          <div className="md:hidden flex border-b border-white/5 flex-shrink-0">
            {SIDE_TABS.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center gap-1 py-2.5 text-xs font-medium transition ${
                    activeTab === tab.id
                      ? 'text-[#dfff1e] border-b-2 border-[#dfff1e]'
                      : 'text-white/40'
                  }`}
                >
                  <Icon size={12} /> {tab.label}
                </button>
              );
            })}
          </div>

          <div className="flex-1 min-h-0 overflow-hidden">
            {activeTab === 'chat' && (
              <ChatPanel
                messages={messages}
                draft={draft}
                setDraft={setDraft}
                onSend={sendMessage}
                isSending={isSending}
                canChat={canChat}
                status={story?.status || 'draft'}
                error={chatError}
                messagesEndRef={messagesEndRef}
              />
            )}
            {activeTab === 'assets' && (
              <AssetsPanel
                scenes={scenes}
                characters={characters}
                storyId={storyId}
                refreshKey={activeJob ? `${activeJob.id}:${activeJob.status}` : 'idle'}
              />
            )}
            {activeTab === 'settings' && (
              <SettingsPanel
                story={story}
                onApproveOutline={approveOutline}
                onGenerate={launchGeneration}
                isWorking={isWorking}
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

// ChevronLeft wasn't imported — add a local fallback
function ChevronLeft({ size = 16, ...props }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}
