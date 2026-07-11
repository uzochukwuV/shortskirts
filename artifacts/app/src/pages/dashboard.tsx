import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation } from "wouter";
import { api, WorkflowType } from "@/lib/api";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import {
  Plus, Clock, ArrowRight, Loader2, CheckCircle2,
  ChevronLeft, ChevronRight, Clapperboard,
  Users, Briefcase, BookOpen, Gamepad2, TrendingUp,
  Sparkles,
} from "lucide-react";
import { format } from "date-fns";

// ─── Workflow types ─────────────────────────────────────────────────────────

type WFConfig = {
  id: WorkflowType;
  icon: React.ReactNode;
  label: string;
  tagline: string;
  defaultGenre: string;
  defaultStyle: string;
  defaultEpisodes: number;
  defaultScenes: number;
  promptLabel: string;
  promptHint: string;
  color: string;
  bg: string;
};

const WORKFLOWS: WFConfig[] = [
  {
    id: "creator_series",
    icon: <Sparkles className="h-5 w-5" />,
    label: "Creator Series",
    tagline: "Serialized anime / fiction series with persistent characters",
    defaultGenre: "action", defaultStyle: "anime", defaultEpisodes: 3, defaultScenes: 5,
    promptLabel: "Story Premise",
    promptHint: "A rogue mech pilot discovers an ancient civilization beneath the megacity…",
    color: "text-violet-600", bg: "bg-violet-50",
  },
  {
    id: "brand_campaign",
    icon: <Briefcase className="h-5 w-5" />,
    label: "Brand Campaign",
    tagline: "Product brief → 15/30/60s ad concepts with clear CTAs",
    defaultGenre: "slice-of-life", defaultStyle: "modern-anime", defaultEpisodes: 1, defaultScenes: 3,
    promptLabel: "Product / Service Brief",
    promptHint: "EcoRun sneakers — sustainable running shoes for urban athletes. Target: 25–35 active city dwellers. CTA: Shop now at ecorun.com",
    color: "text-blue-600", bg: "bg-blue-50",
  },
  {
    id: "social_short",
    icon: <TrendingUp className="h-5 w-5" />,
    label: "Social Short",
    tagline: "TikTok / Reels / YouTube Shorts — hook → payoff format",
    defaultGenre: "action", defaultStyle: "modern-anime", defaultEpisodes: 1, defaultScenes: 3,
    promptLabel: "Content Hook",
    promptHint: "3 signs you're training wrong — fitness myth-busting series, energetic anime style, fast cuts",
    color: "text-emerald-600", bg: "bg-emerald-50",
  },
  {
    id: "educational",
    icon: <BookOpen className="h-5 w-5" />,
    label: "Educational Explainer",
    tagline: "Animated lessons with guide characters and clear concept beats",
    defaultGenre: "slice-of-life", defaultStyle: "anime", defaultEpisodes: 1, defaultScenes: 5,
    promptLabel: "Topic / Lesson Brief",
    promptHint: "How neural networks learn — explain backpropagation to high school students using a curious robot character",
    color: "text-amber-600", bg: "bg-amber-50",
  },
  {
    id: "game_lore",
    icon: <Gamepad2 className="h-5 w-5" />,
    label: "Game / Lore",
    tagline: "IP bible → cinematic lore trailers and character teasers",
    defaultGenre: "fantasy", defaultStyle: "anime", defaultEpisodes: 1, defaultScenes: 4,
    promptLabel: "IP / World Brief",
    promptHint: "Aethermoor — a dying world where rogue AIs and ancient dragons battle for control of the last mana wells",
    color: "text-rose-600", bg: "bg-rose-50",
  },
];

// ─── Wizard state ────────────────────────────────────────────────────────────

type FormData = {
  workflow: WorkflowType;
  title: string;
  prompt: string;
  genre: string;
  style: string;
  num_episodes: number;
  num_scenes: number;
};

const defaultForm = (wf: WFConfig): FormData => ({
  workflow: wf.id,
  title: "",
  prompt: "",
  genre: wf.defaultGenre,
  style: wf.defaultStyle,
  num_episodes: wf.defaultEpisodes,
  num_scenes: wf.defaultScenes,
});

const STEPS = ["Workflow", "Brief", "Scale", "Review"];

// ─── Step components ────────────────────────────────────────────────────────

function StepWorkflow({ form, set }: { form: FormData; set: (p: Partial<FormData>) => void }) {
  return (
    <div className="space-y-2">
      {WORKFLOWS.map(wf => (
        <button
          key={wf.id}
          type="button"
          onClick={() => {
            const cfg = WORKFLOWS.find(w => w.id === wf.id)!;
            set({
              workflow: wf.id,
              genre: cfg.defaultGenre,
              style: cfg.defaultStyle,
              num_episodes: cfg.defaultEpisodes,
              num_scenes: cfg.defaultScenes,
            });
          }}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border text-left transition-all ${
            form.workflow === wf.id
              ? "border-violet-400 bg-violet-50 shadow-sm"
              : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
          }`}
        >
          <span className={`${form.workflow === wf.id ? wf.color : "text-gray-400"} shrink-0`}>{wf.icon}</span>
          <div className="flex-1 min-w-0">
            <div className={`text-sm font-medium ${form.workflow === wf.id ? "text-gray-900" : "text-gray-700"}`}>
              {wf.label}
            </div>
            <div className="text-xs text-gray-400 truncate">{wf.tagline}</div>
          </div>
          {form.workflow === wf.id && <CheckCircle2 className="h-4 w-4 text-violet-500 shrink-0" />}
        </button>
      ))}
    </div>
  );
}

function StepBrief({ form, set }: { form: FormData; set: (p: Partial<FormData>) => void }) {
  const wf = WORKFLOWS.find(w => w.id === form.workflow)!;
  return (
    <div className="space-y-4">
      <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${wf.bg} border border-current/10`}>
        <span className={wf.color}>{wf.icon}</span>
        <span className={`text-xs font-medium ${wf.color}`}>{wf.label}</span>
      </div>
      <div className="space-y-1.5">
        <Label className="text-sm font-medium text-gray-700">Working Title</Label>
        <Input
          value={form.title}
          onChange={e => set({ title: e.target.value })}
          placeholder="e.g. Project Aethermoor"
          className="h-10 border-gray-200 focus:border-violet-400"
        />
      </div>
      <div className="space-y-1.5">
        <Label className="text-sm font-medium text-gray-700">{wf.promptLabel}</Label>
        <Textarea
          value={form.prompt}
          onChange={e => set({ prompt: e.target.value })}
          placeholder={wf.promptHint}
          className="h-28 resize-none border-gray-200 focus:border-violet-400 text-sm"
        />
        <p className="text-xs text-gray-400">Qwen will expand this into a full plan using the {wf.label} template.</p>
      </div>
    </div>
  );
}

function StepScale({ form, set }: { form: FormData; set: (p: Partial<FormData>) => void }) {
  const wf = WORKFLOWS.find(w => w.id === form.workflow)!;
  const totalClips = form.num_episodes * form.num_scenes;
  return (
    <div className="space-y-7">
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <Label className="text-sm font-medium text-gray-700">
            {wf.id === "brand_campaign" ? "Ad Concepts (Episodes)" : "Episodes to Plan"}
          </Label>
          <span className="text-sm font-bold text-violet-600">{form.num_episodes}</span>
        </div>
        <input type="range" min={1} max={5} value={form.num_episodes}
          onChange={e => set({ num_episodes: +e.target.value })}
          className="w-full accent-violet-600" />
        <div className="flex justify-between text-xs text-gray-400"><span>1</span><span>5</span></div>
      </div>
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <Label className="text-sm font-medium text-gray-700">
            {wf.id === "brand_campaign" ? "Scenes per Ad" : "Scenes per Episode"}
          </Label>
          <span className="text-sm font-bold text-violet-600">{form.num_scenes}</span>
        </div>
        <input type="range" min={3} max={10} value={form.num_scenes}
          onChange={e => set({ num_scenes: +e.target.value })}
          className="w-full accent-violet-600" />
        <div className="flex justify-between text-xs text-gray-400"><span>3</span><span>10</span></div>
      </div>
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2 text-sm">
        <div className="flex justify-between text-gray-500">
          <span>Total clips to render</span>
          <span className="font-semibold text-gray-800">{totalClips}</span>
        </div>
        <div className="flex justify-between text-gray-500">
          <span>Est. render time</span>
          <span className="font-semibold text-gray-800">~{totalClips * 2}–{totalClips * 4} min</span>
        </div>
        <p className="text-xs text-gray-400 pt-1 border-t border-gray-200">
          You'll review and approve the outline before any video renders.
        </p>
      </div>
    </div>
  );
}

function StepReview({ form }: { form: FormData }) {
  const wf = WORKFLOWS.find(w => w.id === form.workflow)!;
  return (
    <div className="space-y-4">
      <div className="bg-violet-50 border border-violet-200 rounded-xl p-5 space-y-2">
        <div className={`flex items-center gap-2 text-xs font-semibold ${wf.color}`}>
          {wf.icon} {wf.label}
        </div>
        <h3 className="font-semibold text-gray-900 text-lg">{form.title || "Untitled"}</h3>
        <p className="text-sm text-gray-600 leading-relaxed line-clamp-3">{form.prompt || "No brief provided."}</p>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        {[
          { label: "Genre",    value: form.genre },
          { label: "Style",    value: form.style },
          { label: "Episodes", value: form.num_episodes },
          { label: "Scenes",   value: `${form.num_scenes} / ep` },
        ].map(r => (
          <div key={r.label} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <p className="text-xs text-gray-400 mb-0.5">{r.label}</p>
            <p className="font-medium text-gray-800 capitalize">{r.value}</p>
          </div>
        ))}
      </div>
      <div className="text-xs text-gray-400 bg-amber-50 border border-amber-200 rounded-lg p-3">
        <strong className="text-amber-700">Approval gate:</strong> Qwen generates the plan immediately. You review and approve the outline before any video clip renders — no wasted generations.
      </div>
    </div>
  );
}

// ─── Wizard dialog ──────────────────────────────────────────────────────────

function NewProductionDialog({ onCreated }: { onCreated: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [form, setFormRaw] = useState<FormData>(defaultForm(WORKFLOWS[0]));
  const qc = useQueryClient();

  const set = (p: Partial<FormData>) => setFormRaw(f => ({ ...f, ...p }));

  const createMutation = useMutation({
    mutationFn: () =>
      api.createStory({
        title: form.title,
        prompt: form.prompt,
        genre: form.genre,
        style: form.style,
        num_episodes: form.num_episodes,
        num_scenes: form.num_scenes,
        workflow_type: form.workflow,
      }),
    onSuccess: data => {
      qc.invalidateQueries({ queryKey: ["stories"] });
      setOpen(false); setStep(0); setFormRaw(defaultForm(WORKFLOWS[0]));
      onCreated(data.id);
    },
  });

  const canNext = () => {
    if (step === 1) return form.title.trim().length > 0 && form.prompt.trim().length > 10;
    return true;
  };

  const handleOpen = (v: boolean) => {
    setOpen(v);
    if (!v) { setStep(0); setFormRaw(defaultForm(WORKFLOWS[0])); }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogTrigger asChild>
        <Button className="bg-gray-900 hover:bg-gray-700 text-white font-medium px-4 h-9 rounded-lg text-sm">
          <Plus className="mr-2 h-4 w-4" /> New Production
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md border-gray-200 bg-white p-0 overflow-hidden">
        <DialogHeader className="px-6 pt-6 pb-0">
          <DialogTitle className="text-base font-semibold text-gray-900">New Production</DialogTitle>
          <div className="mt-4">
            <div className="flex gap-1 mb-2">
              {STEPS.map((_, i) => (
                <div key={i} className={`h-1.5 flex-1 rounded-full transition-all ${i <= step ? "bg-violet-500" : "bg-gray-200"}`} />
              ))}
            </div>
            <div className="flex justify-between text-[11px] text-gray-400">
              {STEPS.map((s, i) => (
                <span key={s} className={i === step ? "text-violet-600 font-medium" : ""}>{s}</span>
              ))}
            </div>
          </div>
        </DialogHeader>

        <div className="px-6 py-5 min-h-[340px] overflow-y-auto max-h-[60vh]">
          {step === 0 && <StepWorkflow form={form} set={set} />}
          {step === 1 && <StepBrief form={form} set={set} />}
          {step === 2 && <StepScale form={form} set={set} />}
          {step === 3 && <StepReview form={form} />}
        </div>

        <div className="px-6 pb-6 flex items-center justify-between border-t border-gray-100 pt-4">
          <Button type="button" variant="ghost" size="sm"
            onClick={() => step === 0 ? handleOpen(false) : setStep(s => s - 1)}
            className="text-gray-500 hover:text-gray-700">
            {step === 0 ? "Cancel" : <><ChevronLeft className="h-4 w-4 mr-1" /> Back</>}
          </Button>

          {step < STEPS.length - 1 ? (
            <Button size="sm" onClick={() => setStep(s => s + 1)} disabled={!canNext()}
              className="bg-violet-600 hover:bg-violet-700 text-white px-5 rounded-lg">
              Continue <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          ) : (
            <Button size="sm" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}
              className="bg-gray-900 hover:bg-gray-700 text-white px-5 rounded-lg">
              {createMutation.isPending
                ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating plan…</>
                : "Create & Review Plan"}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ─── Status helpers ─────────────────────────────────────────────────────────

function statusBadge(status: string) {
  const s = status === "ready" ? "completed" : status;
  switch (s) {
    case "draft":      return "bg-amber-50 text-amber-600 border-amber-200";
    case "approved":   return "bg-blue-50 text-blue-600 border-blue-200";
    case "generating": return "bg-violet-50 text-violet-600 border-violet-200 animate-pulse";
    case "completed":  return "bg-green-50 text-green-600 border-green-200";
    case "failed":     return "bg-red-50 text-red-600 border-red-200";
    default:           return "bg-gray-100 text-gray-500 border-gray-200";
  }
}

function wfIcon(wf: string) {
  const w = WORKFLOWS.find(x => x.id === wf);
  return w ? <span className={w.color}>{w.icon}</span> : <Sparkles className="h-4 w-4 text-gray-400" />;
}

// ─── Dashboard page ─────────────────────────────────────────────────────────

export default function Dashboard() {
  const [, setLocation] = useLocation();

  const { data: stories, isLoading } = useQuery({
    queryKey: ["stories"],
    queryFn: api.getStories,
    refetchInterval: (data) =>
      (data as any)?.some?.((s: any) => s.status === "generating") ? 6000 : false,
  });

  const total     = stories?.length ?? 0;
  const pendingApproval = stories?.filter(s => s.status === "draft").length ?? 0;
  const active    = stories?.filter(s => s.status === "generating").length ?? 0;
  const completed = stories?.filter(s => s.status === "completed" || s.status === "ready").length ?? 0;

  return (
    <Layout>
      <div className="bg-white min-h-screen">
        <div className="border-b border-gray-100 bg-white">
          <div className="container px-4 md:px-6 py-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 max-w-7xl mx-auto">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Productions</h1>
              <p className="text-sm text-gray-500 mt-0.5">Your AI-generated video series, campaigns, and content.</p>
            </div>
            <NewProductionDialog onCreated={id => setLocation(`/stories/${id}`)} />
          </div>
        </div>

        <div className="container px-4 md:px-6 py-6 max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: "Total",            value: total,          color: "text-gray-900" },
              { label: "Awaiting Review",  value: pendingApproval, color: "text-amber-600" },
              { label: "In Production",    value: active,          color: "text-violet-600" },
              { label: "Completed",        value: completed,       color: "text-green-600" },
            ].map(s => (
              <div key={s.label} className="bg-white border border-gray-200 rounded-xl p-4">
                <p className="text-xs text-gray-400 mb-1">{s.label}</p>
                <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
            </div>
          ) : !stories || stories.length === 0 ? (
            <div className="text-center py-24 border border-dashed border-gray-200 rounded-2xl bg-gray-50">
              <div className="w-12 h-12 rounded-2xl bg-violet-50 flex items-center justify-center mx-auto mb-4">
                <Clapperboard className="h-6 w-6 text-violet-500" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">No productions yet</h3>
              <p className="text-sm text-gray-500 max-w-sm mx-auto mb-6">
                Pick a workflow type, write your brief, and Qwen generates the full plan for your review.
              </p>
              <NewProductionDialog onCreated={id => setLocation(`/stories/${id}`)} />
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {stories.map(story => {
                const displayStatus = story.status === "ready" ? "completed" : story.status;
                return (
                  <Link key={story.id} href={`/stories/${story.id}`}>
                    <div className="group bg-white border border-gray-200 hover:border-violet-300 hover:shadow-sm rounded-2xl p-5 cursor-pointer transition-all flex flex-col h-full">
                      <div className="flex items-start justify-between mb-3">
                        <Badge className={`text-[10px] font-medium border px-2 py-0.5 rounded-full ${statusBadge(story.status)}`}>
                          {displayStatus}
                        </Badge>
                        <span className="text-xs text-gray-400">
                          {story.created_at ? format(new Date(story.created_at), "MMM d") : ""}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 mb-2">
                        {wfIcon(story.workflow_type || "creator_series")}
                        <h3 className="font-semibold text-gray-900 group-hover:text-violet-600 transition-colors line-clamp-1 text-sm">
                          {story.title}
                        </h3>
                      </div>

                      <p className="text-sm text-gray-500 line-clamp-2 flex-1 leading-relaxed">
                        {story.prompt}
                      </p>

                      {story.status === "draft" && (
                        <div className="mt-3 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700 font-medium">
                          ⏳ Outline ready — approve to generate
                        </div>
                      )}

                      <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-100">
                        <div className="flex items-center gap-1 text-xs text-gray-400">
                          <Clock className="h-3 w-3" />
                          <span>{story.genre}</span>
                        </div>
                        <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-violet-500 group-hover:translate-x-0.5 transition-all" />
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
