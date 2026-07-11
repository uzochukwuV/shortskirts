import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRoute, Link } from "wouter";
import { api, Story, Character, Episode, Scene, GenerationJob } from "@/lib/api";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ChevronLeft, Play, Download, User, Film, BookOpen, AlertCircle,
  Loader2, CheckCircle2, Circle, Zap, Users, Clapperboard, Package,
  Clock, Lock, RefreshCw, ThumbsUp, ThumbsDown, Video, ShieldCheck,
  RotateCcw,
} from "lucide-react";

// ─── Pipeline stage inference ──────────────────────────────────────────────

type Stage = "plan" | "characters" | "scenes" | "assembly" | "done";
const STAGES: { id: Stage; label: string; icon: React.ReactNode }[] = [
  { id: "plan",       label: "Plan",       icon: <Zap className="h-3.5 w-3.5" /> },
  { id: "characters", label: "Characters", icon: <Users className="h-3.5 w-3.5" /> },
  { id: "scenes",     label: "Scenes",     icon: <Clapperboard className="h-3.5 w-3.5" /> },
  { id: "assembly",   label: "Assembly",   icon: <Package className="h-3.5 w-3.5" /> },
  { id: "done",       label: "Done",       icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
];

function inferStage(job: GenerationJob): Stage {
  if (job.status === "completed") return "done";
  const s = (job.current_step || "").toLowerCase();
  if (s.includes("assembl")) return "assembly";
  if (s.includes("scene") || s.includes("clip") || s.includes("render")) return "scenes";
  if (s.includes("char") || s.includes("ref") || s.includes("image")) return "characters";
  return "plan";
}

function stageIdx(s: Stage) { return STAGES.findIndex(x => x.id === s); }
function fmt(sec: number) { const m = Math.floor(sec / 60); return m > 0 ? `${m}m ${sec % 60}s` : `${sec}s`; }

// ─── Pipeline progress panel ────────────────────────────────────────────────

function PipelinePanel({ job, completedScenes, totalScenes }: {
  job: GenerationJob; completedScenes: number; totalScenes: number;
}) {
  const [elapsed, setElapsed] = useState(0);
  const t0 = useRef(Date.now());
  useEffect(() => {
    t0.current = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - t0.current) / 1000)), 1000);
    return () => clearInterval(id);
  }, [job.id]);

  const currentStage = inferStage(job);
  const ci = stageIdx(currentStage);
  const pct = job.total_steps > 0 ? Math.round((job.progress / job.total_steps) * 100) : 0;

  return (
    <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-200 bg-blue-100/50">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute h-full w-full rounded-full bg-blue-400 opacity-75" />
            <span className="relative rounded-full h-2 w-2 bg-blue-500" />
          </span>
          <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">Pipeline Active</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-blue-600">
          <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {fmt(elapsed)}</span>
          <span className="font-bold">{pct}%</span>
        </div>
      </div>

      <div className="px-4 pt-3">
        <Progress value={pct} className="h-1.5 bg-blue-200" />
        <p className="text-xs text-blue-600 mt-1.5 font-mono truncate">{job.current_step || "Initialising…"}</p>
      </div>

      <div className="px-4 pb-4 pt-3 grid grid-cols-5 gap-1">
        {STAGES.map((stage, idx) => {
          const done = idx < ci;
          const active = idx === ci && job.status !== "completed";
          const all = job.status === "completed";
          return (
            <div key={stage.id} className="flex flex-col items-center gap-1.5">
              <div className="flex items-center w-full">
                {idx > 0 && <div className={`flex-1 h-px ${done || all ? "bg-blue-500" : "bg-blue-200"}`} />}
                <div className={`flex items-center justify-center w-7 h-7 rounded-full border transition-all ${
                  all || done ? "bg-blue-500 border-blue-500 text-white"
                  : active    ? "bg-white border-blue-400 text-blue-500 ring-2 ring-blue-300"
                              : "bg-white border-blue-200 text-blue-300"
                }`}>
                  {active ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  : done || all ? <CheckCircle2 className="h-3.5 w-3.5" />
                  : <Circle className="h-3.5 w-3.5" />}
                </div>
                {idx < STAGES.length - 1 && <div className={`flex-1 h-px ${done || all ? "bg-blue-500" : "bg-blue-200"}`} />}
              </div>
              <span className={`text-[9px] font-semibold uppercase tracking-wider text-center ${
                active ? "text-blue-600" : done || all ? "text-blue-500" : "text-blue-300"
              }`}>{stage.label}</span>
            </div>
          );
        })}
      </div>

      {(currentStage === "scenes" || currentStage === "assembly") && totalScenes > 0 && (
        <div className="px-4 py-3 border-t border-blue-200 bg-blue-100/30 flex justify-between text-xs text-blue-600">
          <span>Scenes Rendered</span>
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              {Array.from({ length: totalScenes }).map((_, i) => (
                <div key={i} className={`h-1.5 w-5 rounded-full ${i < completedScenes ? "bg-blue-500" : "bg-blue-200"}`} />
              ))}
            </div>
            <span className="font-bold">{completedScenes}/{totalScenes}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Approval gate UI ─────────────────────────────────────────────────────────

function ApprovalGate({ story, onApprove, isApproving }: {
  story: Story; onApprove: () => void; isApproving: boolean;
}) {
  const plan = story.episode_plan;
  return (
    <div className="mt-5 border border-amber-200 bg-amber-50 rounded-xl overflow-hidden">
      <div className="px-5 py-3 bg-amber-100 border-b border-amber-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-amber-600" />
          <span className="text-sm font-semibold text-amber-800">Outline ready — your approval required</span>
        </div>
        <Badge className="bg-amber-200 text-amber-700 border-amber-300 text-[10px]">Approval Gate</Badge>
      </div>

      <div className="p-5 space-y-4">
        {plan && (
          <div className="space-y-3 text-sm">
            <p className="text-gray-700 leading-relaxed"><strong>Synopsis:</strong> {plan.synopsis}</p>
            {plan.characters?.length > 0 && (
              <div>
                <p className="font-medium text-gray-600 mb-1">Cast ({plan.characters.length})</p>
                <div className="flex flex-wrap gap-2">
                  {plan.characters.map((c: any) => (
                    <span key={c.name} className="inline-flex items-center gap-1 px-2.5 py-1 bg-white border border-gray-200 rounded-full text-xs text-gray-600">
                      <User className="h-3 w-3 text-violet-400" /> {c.name}
                      <span className="text-gray-400">· {c.role}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
            {plan.episodes?.map((ep: any) => (
              <div key={ep.episode_number} className="bg-white border border-gray-200 rounded-lg p-3">
                <p className="font-medium text-gray-800 text-xs mb-1">
                  Episode {ep.episode_number}: {ep.title}
                </p>
                <p className="text-xs text-gray-500 leading-relaxed">{ep.summary}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {ep.scenes?.map((sc: any) => (
                    <span key={sc.scene_number} className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded">
                      {sc.title || `Scene ${sc.scene_number}`}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <Button
            onClick={onApprove}
            disabled={isApproving}
            className="bg-gray-900 hover:bg-gray-700 text-white font-medium px-5 h-9 rounded-lg text-sm"
          >
            {isApproving
              ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Approving…</>
              : <><CheckCircle2 className="mr-2 h-4 w-4" /> Approve Outline & Unlock Generation</>}
          </Button>
          <span className="text-xs text-gray-400">No video renders until you approve.</span>
        </div>
      </div>
    </div>
  );
}

// ─── Scene card with granular actions ────────────────────────────────────────

function SceneCard({ scene, story, onRegenerate, onApprove, onReject, onLock }: {
  scene: Scene; story: Story;
  onRegenerate: () => void;
  onApprove: () => void;
  onReject: () => void;
  onLock: () => void;
}) {
  const isGenerating = scene.status === "running";
  const hasVideo = !!(scene.video_url || scene.clip_url);
  const videoSrc = scene.video_url || scene.clip_url;

  return (
    <div className={`border rounded-xl overflow-hidden bg-white transition-all ${
      scene.approval_status === "approved" ? "border-green-200" :
      scene.approval_status === "rejected" ? "border-red-200" :
      "border-gray-200"
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="font-mono text-[10px] bg-white">
            SCENE {String(scene.scene_number).padStart(3, "0")}
          </Badge>
          <span className="font-medium text-gray-900 text-sm">{scene.title || `Scene ${scene.scene_number}`}</span>
          {scene.locked && <Lock className="h-3.5 w-3.5 text-gray-400" />}
          {scene.regeneration_count > 0 && (
            <span className="text-[10px] text-gray-400">· {scene.regeneration_count}× regen</span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {/* Status badge */}
          {scene.approval_status === "approved" && (
            <span className="flex items-center gap-1 text-[10px] font-medium text-green-600 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
              <CheckCircle2 className="h-3 w-3" /> Approved
            </span>
          )}
          {scene.approval_status === "rejected" && (
            <span className="text-[10px] font-medium text-red-600 bg-red-50 border border-red-200 rounded-full px-2 py-0.5">
              Rejected
            </span>
          )}
          {scene.mood && (
            <span className="text-[10px] text-gray-400 bg-white border border-gray-200 rounded-full px-2 py-0.5">
              {scene.mood}
            </span>
          )}
          {scene.location && (
            <span className="text-[10px] text-gray-400 bg-white border border-gray-200 rounded-full px-2 py-0.5">
              {scene.location}
            </span>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-0 divide-y md:divide-y-0 md:divide-x divide-gray-200">
        {/* Left: scene info */}
        <div className="p-4 space-y-3">
          {scene.description && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-1">Action</div>
              <p className="text-sm text-gray-700 leading-relaxed">{scene.description}</p>
            </div>
          )}
          {scene.visual_prompt && (
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-1">Visual Prompt</div>
              <p className="text-xs text-gray-500 font-mono bg-gray-50 border border-gray-200 p-2 rounded-lg leading-relaxed">
                {scene.visual_prompt}
              </p>
            </div>
          )}
          {/* Action buttons */}
          {hasVideo && !scene.locked && (
            <div className="pt-2 flex flex-wrap gap-2">
              <Button size="sm" variant="outline"
                onClick={onApprove}
                disabled={scene.approval_status === "approved"}
                className="h-7 text-xs border-green-200 text-green-700 hover:bg-green-50 rounded-lg">
                <ThumbsUp className="h-3 w-3 mr-1" /> Approve
              </Button>
              <Button size="sm" variant="outline"
                onClick={onReject}
                disabled={scene.approval_status === "rejected"}
                className="h-7 text-xs border-red-200 text-red-600 hover:bg-red-50 rounded-lg">
                <ThumbsDown className="h-3 w-3 mr-1" /> Reject
              </Button>
              <Button size="sm" variant="outline"
                onClick={onRegenerate}
                disabled={isGenerating}
                className="h-7 text-xs border-gray-200 text-gray-600 hover:bg-gray-50 rounded-lg">
                {isGenerating
                  ? <><Loader2 className="h-3 w-3 mr-1 animate-spin" /> Regenerating</>
                  : <><RefreshCw className="h-3 w-3 mr-1" /> Regenerate</>}
              </Button>
              {scene.approval_status === "approved" && (
                <Button size="sm" variant="outline" onClick={onLock}
                  className="h-7 text-xs border-gray-200 text-gray-500 hover:bg-gray-50 rounded-lg">
                  <Lock className="h-3 w-3 mr-1" /> Lock
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Right: video */}
        <div className="p-4 flex flex-col justify-center items-center bg-gray-50 min-h-[200px] relative group">
          {isGenerating ? (
            <div className="flex flex-col items-center gap-2 text-gray-400">
              <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
              <span className="text-xs">Regenerating…</span>
            </div>
          ) : hasVideo ? (
            <>
              <video src={videoSrc} controls className="w-full rounded-lg max-h-[220px] object-contain" />
              <a href={videoSrc} download
                className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity bg-white border border-gray-200 text-gray-600 hover:text-gray-900 p-1.5 rounded-lg shadow-sm">
                <Download className="h-3.5 w-3.5" />
              </a>
            </>
          ) : story.status === "generating" ? (
            <div className="flex flex-col items-center gap-2 text-gray-400">
              <Loader2 className="h-8 w-8 animate-spin text-gray-300" />
              <span className="text-xs">Awaiting render</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-gray-300">
              <Video className="h-8 w-8" />
              <span className="text-xs">No render yet</span>
              {!scene.locked && (
                <Button size="sm" variant="outline" onClick={onRegenerate}
                  className="mt-2 h-7 text-xs border-violet-200 text-violet-600 hover:bg-violet-50 rounded-lg">
                  <RotateCcw className="h-3 w-3 mr-1" /> Generate this scene
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Character card with approval + regen ────────────────────────────────────

function CharacterCard({ char, onApprove, onLock, onRegenRefs }: {
  char: Character;
  onApprove: () => void;
  onLock: () => void;
  onRegenRefs: () => void;
}) {
  return (
    <div className={`bg-white border rounded-2xl overflow-hidden transition-all ${
      char.approval_status === "approved" ? "border-green-200" : "border-gray-200"
    }`}>
      {/* Ref image */}
      <div className="aspect-[4/3] bg-gray-100 relative overflow-hidden">
        {char.ref_image_urls?.[0] ? (
          <img src={char.ref_image_urls[0]} alt={char.name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <User className="h-10 w-10 text-gray-300" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-gray-900/40 to-transparent" />
        {char.approval_status === "approved" && (
          <div className="absolute top-2 right-2 bg-green-500 text-white rounded-full p-0.5">
            <CheckCircle2 className="h-3.5 w-3.5" />
          </div>
        )}
        {char.locked && (
          <div className="absolute top-2 left-2 bg-gray-800/70 text-white rounded-full p-1">
            <Lock className="h-3 w-3" />
          </div>
        )}
      </div>

      <div className="p-4">
        <div className="flex items-start justify-between mb-1">
          <h3 className="font-semibold text-gray-900">{char.name}</h3>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-violet-500 bg-violet-50 border border-violet-200 px-2 py-0.5 rounded-full">
            {char.role}
          </span>
        </div>
        <p className="text-xs text-gray-500 line-clamp-2 mb-3 leading-relaxed">{char.description}</p>
        {char.appearance && (
          <p className="text-[11px] text-gray-400 line-clamp-1 mb-3">{char.appearance}</p>
        )}

        {/* Ref thumbnails */}
        {char.ref_image_urls?.length > 1 && (
          <div className="flex gap-1 mb-3">
            {char.ref_image_urls.slice(0, 3).map((url, i) => (
              <img key={i} src={url} alt="" className="h-10 w-10 rounded-lg object-cover border border-gray-200" />
            ))}
          </div>
        )}

        {/* Actions */}
        {!char.locked && (
          <div className="flex flex-wrap gap-1.5">
            {char.approval_status !== "approved" && (
              <Button size="sm" variant="outline" onClick={onApprove}
                className="h-7 text-xs border-green-200 text-green-700 hover:bg-green-50 rounded-lg">
                <ThumbsUp className="h-3 w-3 mr-1" /> Approve
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={onRegenRefs}
              className="h-7 text-xs border-gray-200 text-gray-600 hover:bg-gray-50 rounded-lg">
              <RefreshCw className="h-3 w-3 mr-1" /> New Refs
            </Button>
            {char.approval_status === "approved" && (
              <Button size="sm" variant="outline" onClick={onLock}
                className="h-7 text-xs border-gray-200 text-gray-500 hover:bg-gray-50 rounded-lg">
                <Lock className="h-3 w-3 mr-1" /> Lock
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function StoryDetail() {
  const [, params] = useRoute("/stories/:id");
  const id = params?.id || "";
  const qc = useQueryClient();
  const [activeEp, setActiveEp] = useState<string>("");

  const isGenerating = (s?: string) => s === "generating";
  const needsApproval = (s?: string) => s === "draft";

  const { data: story, isLoading: loadingStory } = useQuery({
    queryKey: ["story", id],
    queryFn: () => api.getStory(id),
    enabled: !!id,
    refetchInterval: d => (isGenerating((d as Story | undefined)?.status) ? 5000 : false),
  });

  const { data: characters } = useQuery({
    queryKey: ["characters", id],
    queryFn: () => api.getCharacters(id),
    enabled: !!id,
    refetchInterval: isGenerating(story?.status) ? 8000 : false,
  });

  const { data: episodes } = useQuery({
    queryKey: ["episodes", id],
    queryFn: () => api.getEpisodes(id),
    enabled: !!id,
    refetchInterval: isGenerating(story?.status) ? 5000 : false,
  });

  const { data: jobs } = useQuery({
    queryKey: ["jobs", "story", id],
    queryFn: () => api.getEntityJobs("story", id),
    enabled: !!id && isGenerating(story?.status),
    refetchInterval: 4000,
  });

  const activeJob = jobs?.find(j => j.status === "running" || j.status === "pending");

  const { data: liveJob } = useQuery({
    queryKey: ["job", activeJob?.id],
    queryFn: () => api.getJob(activeJob!.id),
    refetchInterval: 3000,
    enabled: !!activeJob?.id,
  });

  useEffect(() => {
    if (liveJob?.status === "completed" || liveJob?.status === "failed") {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      qc.invalidateQueries({ queryKey: ["characters", id] });
    }
  }, [liveJob?.status, id, qc]);

  const approveMutation = useMutation({
    mutationFn: () => api.approveOutline(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["story", id] }),
  });

  const generateMutation = useMutation({
    mutationFn: () => api.generateStory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["jobs", "story", id] });
    },
  });

  const sceneRegenMutation = useMutation({
    mutationFn: (sceneId: string) => api.regenerateScene(sceneId),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: ["episodes", id] }), 2000),
  });

  const sceneApproveMutation = useMutation({
    mutationFn: (sceneId: string) => api.approveScene(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }),
  });

  const sceneRejectMutation = useMutation({
    mutationFn: (sceneId: string) => api.rejectScene(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }),
  });

  const sceneLockMutation = useMutation({
    mutationFn: (sceneId: string) => api.lockScene(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }),
  });

  const charApproveMutation = useMutation({
    mutationFn: (charId: string) => api.approveCharacter(charId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["characters", id] }),
  });

  const charLockMutation = useMutation({
    mutationFn: (charId: string) => api.lockCharacter(charId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["characters", id] }),
  });

  const charRegenMutation = useMutation({
    mutationFn: (charId: string) => api.regenerateCharacterRefs(charId),
    onSuccess: () => setTimeout(() => qc.invalidateQueries({ queryKey: ["characters", id] }), 5000),
  });

  useEffect(() => {
    if (episodes?.length && !activeEp) setActiveEp(episodes[0].id);
  }, [episodes, activeEp]);

  const allScenes = episodes?.flatMap(e => e.scenes ?? []) ?? [];
  const completedScenes = allScenes.filter(s => s.video_url || s.clip_url).length;
  const displayJob = liveJob ?? activeJob;

  if (loadingStory) {
    return (
      <Layout>
        <div className="container p-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
        </div>
      </Layout>
    );
  }

  if (!story) return <Layout><div className="p-8 text-gray-500">Story not found.</div></Layout>;

  const statusColor: Record<string, string> = {
    draft:      "bg-amber-50 text-amber-700 border-amber-200",
    approved:   "bg-blue-50 text-blue-700 border-blue-200",
    generating: "bg-violet-50 text-violet-700 border-violet-200",
    completed:  "bg-green-50 text-green-700 border-green-200",
    ready:      "bg-green-50 text-green-700 border-green-200",
    failed:     "bg-red-50 text-red-700 border-red-200",
  };

  return (
    <Layout>
      {/* ── Header ── */}
      <div className="border-b border-gray-100 bg-white">
        <div className="container px-4 md:px-6 py-5 max-w-7xl mx-auto">
          <div className="flex items-center gap-2 text-sm text-gray-400 mb-4">
            <Link href="/dashboard" className="hover:text-violet-600 flex items-center transition-colors">
              <ChevronLeft className="h-4 w-4 mr-0.5" /> Dashboard
            </Link>
            <span>/</span>
            <span className="text-gray-600">Production Workspace</span>
          </div>

          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h1 className="text-2xl font-bold text-gray-900">{story.title}</h1>
                <Badge className={`border text-[10px] font-semibold uppercase px-2 py-0.5 ${statusColor[story.status] || "bg-gray-100 text-gray-500"}`}>
                  {story.status}
                </Badge>
              </div>
              <p className="text-gray-500 text-sm max-w-2xl leading-relaxed">{story.prompt}</p>
            </div>

            <div className="flex gap-2 shrink-0">
              {story.status === "approved" && (
                <Button
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                  className="bg-gray-900 hover:bg-gray-700 text-white h-9 px-4 rounded-lg text-sm font-medium"
                >
                  {generateMutation.isPending
                    ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Starting…</>
                    : <><Play className="mr-2 h-4 w-4" /> Start Generation</>}
                </Button>
              )}
              {(story.status === "completed" || story.status === "ready") && (
                <Button variant="outline" className="h-9 px-4 rounded-lg text-sm border-gray-200 text-gray-600">
                  <Download className="mr-2 h-4 w-4" /> Export
                </Button>
              )}
            </div>
          </div>

          {/* Approval gate */}
          {needsApproval(story.status) && (
            <ApprovalGate
              story={story}
              onApprove={() => approveMutation.mutate()}
              isApproving={approveMutation.isPending}
            />
          )}

          {/* Pipeline progress */}
          {displayJob && (displayJob.status === "running" || displayJob.status === "pending") && (
            <PipelinePanel
              job={displayJob}
              completedScenes={completedScenes}
              totalScenes={allScenes.length}
            />
          )}

          {story.status === "failed" && (
            <div className="mt-4 p-4 border border-red-200 bg-red-50 rounded-xl flex items-start gap-3">
              <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-semibold text-red-700 mb-1">Generation failed</p>
                <p className="text-xs text-red-500">Check server logs. Approve the outline again and retry.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="container px-4 md:px-6 py-6 max-w-7xl mx-auto">
        <Tabs defaultValue="episodes">
          <TabsList className="bg-gray-100 border border-gray-200 h-auto p-1 rounded-xl mb-6 w-full justify-start">
            {[
              { value: "episodes",   label: "Episodes & Scenes", icon: <Film className="h-4 w-4 mr-1.5" /> },
              { value: "characters", label: `Cast (${characters?.length ?? 0})`, icon: <Users className="h-4 w-4 mr-1.5" /> },
              { value: "plan",       label: "Master Plan", icon: <BookOpen className="h-4 w-4 mr-1.5" /> },
            ].map(t => (
              <TabsTrigger key={t.value} value={t.value}
                className="data-[state=active]:bg-white data-[state=active]:shadow-sm text-sm flex items-center px-4 py-2 rounded-lg font-medium text-gray-500 data-[state=active]:text-gray-900">
                {t.icon}{t.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Episodes & Scenes */}
          <TabsContent value="episodes" className="m-0">
            {!episodes || episodes.length === 0 ? (
              <div className="text-center py-20 border border-dashed border-gray-200 rounded-2xl text-gray-400">
                <Clapperboard className="h-8 w-8 mx-auto mb-3 opacity-40" />
                <p className="text-sm">
                  {story.status === "draft"
                    ? "Approve the outline above to unlock generation."
                    : story.status === "approved"
                    ? "Click 'Start Generation' to begin rendering."
                    : "No episodes generated yet."}
                </p>
              </div>
            ) : (
              <div className="grid md:grid-cols-12 gap-6">
                {/* Episode list */}
                <div className="md:col-span-3">
                  <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3 px-1">Episodes</p>
                  <div className="space-y-1">
                    {episodes.map(ep => {
                      const epScenes = ep.scenes ?? [];
                      const rendered = epScenes.filter(s => s.video_url || s.clip_url).length;
                      const approved = epScenes.filter(s => s.approval_status === "approved").length;
                      return (
                        <button key={ep.id} onClick={() => setActiveEp(ep.id)}
                          className={`w-full text-left px-3 py-3 rounded-xl border transition-all ${
                            activeEp === ep.id
                              ? "bg-violet-50 border-violet-200 text-violet-700"
                              : "border-transparent text-gray-600 hover:bg-gray-50 hover:border-gray-200"
                          }`}>
                          <div className="text-[10px] font-mono uppercase text-gray-400 mb-0.5">Episode {ep.episode_number}</div>
                          <div className="text-sm font-medium line-clamp-1">{ep.title}</div>
                          <div className="mt-2 flex items-center gap-2">
                            <div className="flex gap-0.5 flex-1">
                              {epScenes.map((sc, i) => (
                                <div key={i} className={`h-1 flex-1 rounded-full ${
                                  sc.approval_status === "approved" ? "bg-green-400" :
                                  sc.video_url || sc.clip_url ? "bg-violet-400" : "bg-gray-200"
                                }`} />
                              ))}
                            </div>
                            <span className="text-[10px] text-gray-400">{approved}/{epScenes.length}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Scenes */}
                <div className="md:col-span-9">
                  {(() => {
                    const ep = episodes.find(e => e.id === activeEp);
                    if (!ep) return null;
                    return (
                      <div className="space-y-5">
                        <div className="border-b border-gray-100 pb-4">
                          <h2 className="text-xl font-bold text-gray-900 mb-1">
                            <span className="text-gray-400 mr-2 font-normal">Ep {ep.episode_number}</span>{ep.title}
                          </h2>
                          {ep.summary && <p className="text-sm text-gray-500 leading-relaxed">{ep.summary}</p>}
                          {ep.assembled_video_url && (
                            <a href={ep.assembled_video_url} target="_blank" rel="noreferrer"
                              className="inline-flex items-center gap-2 mt-3 text-sm font-medium text-violet-600 hover:text-violet-700">
                              <Play className="h-4 w-4" /> Watch assembled episode
                            </a>
                          )}
                        </div>

                        {ep.scenes?.length ? ep.scenes.map((scene: Scene) => (
                          <SceneCard key={scene.id} scene={scene} story={story}
                            onRegenerate={() => sceneRegenMutation.mutate(scene.id)}
                            onApprove={() => sceneApproveMutation.mutate(scene.id)}
                            onReject={() => sceneRejectMutation.mutate(scene.id)}
                            onLock={() => sceneLockMutation.mutate(scene.id)}
                          />
                        )) : (
                          <div className="text-center py-12 border border-dashed border-gray-200 rounded-2xl text-gray-400 text-sm">
                            Scenes will appear here once generation starts.
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}
          </TabsContent>

          {/* Characters */}
          <TabsContent value="characters" className="m-0">
            {!characters || characters.length === 0 ? (
              <div className="text-center py-20 border border-dashed border-gray-200 rounded-2xl text-gray-400">
                <Users className="h-8 w-8 mx-auto mb-3 opacity-40" />
                <p className="text-sm">Characters will be materialised when you create the production.</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
                {characters.map(char => (
                  <CharacterCard key={char.id} char={char}
                    onApprove={() => charApproveMutation.mutate(char.id)}
                    onLock={() => charLockMutation.mutate(char.id)}
                    onRegenRefs={() => charRegenMutation.mutate(char.id)}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Master Plan */}
          <TabsContent value="plan" className="m-0">
            {story.episode_plan ? (
              <div className="bg-white border border-gray-200 rounded-2xl p-6 md:p-8 space-y-8 max-w-3xl">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-violet-500 mb-2">Synopsis</h3>
                  <p className="text-gray-700 leading-relaxed text-base">{story.episode_plan.synopsis}</p>
                </div>
                <div className="border-t border-gray-100 pt-6">
                  <h3 className="text-xs font-semibold uppercase tracking-widest text-violet-500 mb-2">Setting</h3>
                  <p className="text-gray-700 leading-relaxed">{story.episode_plan.setting}</p>
                </div>
                {story.episode_plan.themes?.length > 0 && (
                  <div className="border-t border-gray-100 pt-6">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-violet-500 mb-3">Themes</h3>
                    <div className="flex flex-wrap gap-2">
                      {story.episode_plan.themes.map((t: string, i: number) => (
                        <span key={i} className="px-3 py-1 bg-violet-50 border border-violet-200 text-violet-700 text-sm rounded-full">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {story.episode_plan.episodes?.map((ep: any) => (
                  <div key={ep.episode_number} className="border-t border-gray-100 pt-6">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-violet-500 mb-2">
                      Episode {ep.episode_number}: {ep.title}
                    </h3>
                    <p className="text-sm text-gray-600 mb-3">{ep.summary}</p>
                    <div className="space-y-2">
                      {ep.scenes?.map((sc: any) => (
                        <div key={sc.scene_number} className="bg-gray-50 border border-gray-200 rounded-xl p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] font-mono text-gray-400">S{sc.scene_number}</span>
                            <span className="text-sm font-medium text-gray-800">{sc.title}</span>
                            {sc.mood && <span className="text-[10px] text-gray-400 bg-white border border-gray-200 rounded px-1.5 py-0.5">{sc.mood}</span>}
                          </div>
                          <p className="text-xs text-gray-500 leading-relaxed">{sc.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-20 text-gray-400 text-sm">
                No plan generated yet.
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
