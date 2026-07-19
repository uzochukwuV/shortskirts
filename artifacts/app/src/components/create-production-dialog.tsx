import { useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import {
  ArrowRight,
  Clapperboard,
  Loader2,
  Sparkles,
  Upload,
  Video,
  WandSparkles,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { api, WorkflowType } from "@/lib/api";

type RefAsset = {
  url: string;
  name: string;
};

type WorkflowPreset = {
  id: WorkflowType;
  label: string;
  description: string;
  episodes: number;
  scenes: number;
  genre: string;
  style: string;
  frameRatio: "16:9" | "9:16" | "1:1";
};

const WORKFLOWS: WorkflowPreset[] = [
  { id: "creator_series", label: "Creator series", description: "Serialized episodes with recurring cast and approvals.", episodes: 3, scenes: 5, genre: "action", style: "anime", frameRatio: "16:9" },
  { id: "narrated_image_story", label: "Narrated image story", description: "Image-led scenes with voice-over and continuity passes.", episodes: 1, scenes: 6, genre: "drama", style: "anime", frameRatio: "16:9" },
  { id: "brand_campaign", label: "Brand campaign", description: "Fast ad concepts with product framing and CTA.", episodes: 1, scenes: 3, genre: "slice-of-life", style: "modern-anime", frameRatio: "16:9" },
  { id: "social_short", label: "Social short", description: "Hook-heavy short form for vertical feeds.", episodes: 1, scenes: 4, genre: "action", style: "modern-anime", frameRatio: "9:16" },
  { id: "educational", label: "Educational explainer", description: "Structured lessons with a guided visual sequence.", episodes: 1, scenes: 5, genre: "slice-of-life", style: "anime", frameRatio: "16:9" },
  { id: "game_lore", label: "Game lore", description: "Worldbuilding trailers and lore teasers.", episodes: 1, scenes: 4, genre: "fantasy", style: "anime", frameRatio: "16:9" },
];

const STEP_ORDER = ["brief", "format", "refs", "review"] as const;
type StepKey = (typeof STEP_ORDER)[number];

function ReferenceUploadSection({
  label,
  description,
  items,
  onUpload,
  onRemove,
  disabled,
}: {
  label: string;
  description: string;
  items: RefAsset[];
  onUpload: (files: FileList | null) => void;
  onRemove: (url: string) => void;
  disabled?: boolean;
}) {
  const inputId = `${label.toLowerCase().replace(/\s+/g, "-")}-upload`;
  return (
    <div className="space-y-3 rounded-[18px] border border-border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-foreground">{label}</div>
          <div className="mt-1 text-xs leading-5 text-muted-foreground">{description}</div>
        </div>
        <label htmlFor={inputId}>
          <Button variant="outline" size="sm" className="cursor-pointer" asChild>
            <span>
              <Upload className="h-4 w-4" />
              Upload
            </span>
          </Button>
        </label>
        <input
          id={inputId}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          disabled={disabled}
          onChange={(e) => onUpload(e.target.files)}
        />
      </div>
      <div className="grid grid-cols-3 gap-2">
        {items.length > 0 ? (
          items.map((item) => (
            <div key={item.url} className="group relative overflow-hidden rounded-[14px] border border-border bg-muted/20">
              <img src={item.url} alt={item.name} className="h-24 w-full object-cover" />
              <button
                type="button"
                onClick={() => onRemove(item.url)}
                className="absolute right-1 top-1 rounded-full border border-white/20 bg-black/60 p-1 text-white opacity-0 transition-opacity group-hover:opacity-100"
              >
                <span className="sr-only">Remove</span>
                <ChevronRight className="h-3.5 w-3.5 rotate-45" />
              </button>
            </div>
          ))
        ) : (
          <div className="col-span-3 rounded-[14px] border border-dashed border-border bg-muted/20 px-3 py-4 text-xs text-muted-foreground">
            No images uploaded yet.
          </div>
        )}
      </div>
    </div>
  );
}

function StepPill({ active, done, children }: { active?: boolean; done?: boolean; children: string }) {
  return (
    <div
      className={`rounded-[9999px] border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${
        active
          ? "border-[color:#083300] bg-[color:#96ff1a] text-[color:#083300]"
          : done
            ? "border-border bg-muted text-foreground"
            : "border-border bg-white text-muted-foreground"
      }`}
    >
      {children}
    </div>
  );
}

export function CreateProductionDialog({ onCreated }: { onCreated: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowType>("creator_series");
  const preset = WORKFLOWS.find((item) => item.id === selectedWorkflow) ?? WORKFLOWS[0];
  const [step, setStep] = useState<StepKey>("brief");
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [genre, setGenre] = useState(preset.genre);
  const [style, setStyle] = useState(preset.style);
  const [frameRatio, setFrameRatio] = useState<WorkflowPreset["frameRatio"]>(preset.frameRatio);
  const [episodes, setEpisodes] = useState(preset.episodes);
  const [scenes, setScenes] = useState(preset.scenes);
  const [styleRefs, setStyleRefs] = useState<RefAsset[]>([]);
  const [characterRefs, setCharacterRefs] = useState<RefAsset[]>([]);
  const [sceneRefs, setSceneRefs] = useState<RefAsset[]>([]);
  const [uploading, setUploading] = useState(false);
  const qc = useQueryClient();
  const [, setLocation] = useLocation();

  const uploadFiles = async (files: FileList | null, setter: Dispatch<SetStateAction<RefAsset[]>>) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      const uploads = await Promise.all(
        Array.from(files).map(async (file) => {
          const uploaded = await api.uploadImage(file);
          return { url: uploaded.url, name: file.name };
        }),
      );
      setter((prev) => [...prev, ...uploads]);
    } finally {
      setUploading(false);
    }
  };

  const create = useMutation({
    mutationFn: () =>
      api.createStory({
        title,
        prompt,
        genre,
        style,
        frame_ratio: frameRatio,
        num_episodes: episodes,
        num_scenes: scenes,
        workflow_type: selectedWorkflow,
        style_reference_urls: styleRefs.map((item) => item.url),
        character_reference_urls: characterRefs.map((item) => item.url),
        scene_reference_urls: sceneRefs.map((item) => item.url),
      }),
    onSuccess: (story) => {
      qc.invalidateQueries({ queryKey: ["stories"] });
      setOpen(false);
      setStep("brief");
      setTitle("");
      setPrompt("");
      setSelectedWorkflow("creator_series");
      setGenre(WORKFLOWS[0].genre);
      setStyle(WORKFLOWS[0].style);
      setFrameRatio(WORKFLOWS[0].frameRatio);
      setEpisodes(WORKFLOWS[0].episodes);
      setScenes(WORKFLOWS[0].scenes);
      setStyleRefs([]);
      setCharacterRefs([]);
      setSceneRefs([]);
      onCreated(story.id);
      setLocation(`/stories/${story.id}`);
    },
  });

  const setWorkflow = (workflow: WorkflowType) => {
    const next = WORKFLOWS.find((item) => item.id === workflow) ?? WORKFLOWS[0];
    setSelectedWorkflow(workflow);
    setGenre(next.genre);
    setStyle(next.style);
    setFrameRatio(next.frameRatio);
    setEpisodes(next.episodes);
    setScenes(next.scenes);
  };

  const estimatedMinutes = useMemo(() => {
    const base = 6 + scenes * 3 + episodes * 4;
    return Math.max(8, base);
  }, [episodes, scenes]);

  const totalRefs = styleRefs.length + characterRefs.length + sceneRefs.length;
  const currentIndex = STEP_ORDER.indexOf(step);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="lime" size="lg">
          <Clapperboard className="h-4 w-4" />
          Create production
          <ArrowRight className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-[1200px] overflow-hidden border-border bg-white p-0">
        <div className="grid max-h-[90vh] lg:grid-cols-[360px_1fr]">
          <aside className="border-b border-border bg-[color:#121212] p-6 text-white lg:border-b-0 lg:border-r">
            <div className="inline-flex items-center gap-2 rounded-[9999px] border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-white/70">
              <Sparkles className="h-3.5 w-3.5 text-[color:#96ff1a]" />
              Production builder
            </div>
            <DialogTitle className="mt-5 text-[40px] leading-[0.95] tracking-[-0.04em] text-white">
              Build the brief, then generate from a clean state.
            </DialogTitle>
            <p className="mt-4 max-w-sm text-sm leading-6 text-white/70">
              Keep the brief compact, attach reference images, and hand the backend a production-ready story state.
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              <StepPill active={step === "brief"} done={currentIndex > 0}>Brief</StepPill>
              <StepPill active={step === "format"} done={currentIndex > 1}>Format</StepPill>
              <StepPill active={step === "refs"} done={currentIndex > 2}>Refs</StepPill>
              <StepPill active={step === "review"} done={currentIndex > 3}>Review</StepPill>
            </div>

            <div className="mt-8 space-y-2">
              {WORKFLOWS.map((workflow) => (
                <button
                  key={workflow.id}
                  type="button"
                  onClick={() => setWorkflow(workflow.id)}
                  className={`w-full rounded-[18px] border px-4 py-3 text-left transition-colors ${
                    selectedWorkflow === workflow.id
                      ? "border-[color:#96ff1a] bg-white text-[color:#083300]"
                      : "border-white/10 bg-white/5 text-white hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold">{workflow.label}</div>
                    <Badge className="border-0 bg-white/10 text-white">{workflow.frameRatio}</Badge>
                  </div>
                  <div className={`mt-1 text-xs leading-5 ${selectedWorkflow === workflow.id ? "text-[color:#083300]/70" : "text-white/55"}`}>
                    {workflow.description}
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-8 rounded-[18px] border border-white/10 bg-white/5 p-4">
              <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Quick summary</div>
              <div className="mt-3 space-y-2 text-sm text-white">
                <div className="flex items-center justify-between gap-4">
                  <span>Aspect ratio</span>
                  <span className="text-white/70">{frameRatio}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Scenes</span>
                  <span className="text-white/70">{episodes} episodes / {scenes} scenes</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>References</span>
                  <span className="text-white/70">{totalRefs}</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span>Estimated prep</span>
                  <span className="text-white/70">{estimatedMinutes} min</span>
                </div>
              </div>
            </div>
          </aside>

          <div className="flex min-h-0 flex-col">
            <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Creation flow</div>
                <div className="mt-1 text-sm font-semibold text-foreground">
                  {step === "brief" ? "Define the brief" : step === "format" ? "Set the format" : step === "refs" ? "Attach references" : "Review and submit"}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setStep(STEP_ORDER[Math.max(0, currentIndex - 1)])} disabled={currentIndex === 0 || create.isPending}>
                  <ChevronLeft className="h-4 w-4" />
                  Back
                </Button>
                <Button
                  variant={step === "review" ? "lime" : "outline"}
                  size="sm"
                  onClick={() => {
                    if (step === "review") {
                      create.mutate();
                      return;
                    }
                    setStep(STEP_ORDER[Math.min(STEP_ORDER.length - 1, currentIndex + 1)]);
                  }}
                  disabled={create.isPending || uploading || !title.trim() || !prompt.trim()}
                >
                  {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : step === "review" ? <Clapperboard className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  {step === "review" ? "Create production" : "Continue"}
                </Button>
              </div>
            </div>

            <ScrollArea className="min-h-0 flex-1">
              <div className="grid gap-6 p-6 xl:grid-cols-[1.1fr_0.9fr]">
                <div className="space-y-6">
                  {step === "brief" && (
                    <section className="rounded-[22px] border border-border bg-white p-5">
                      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        <WandSparkles className="h-3.5 w-3.5 text-[color:#083300]" />
                        Brief
                      </div>
                      <div className="mt-4 grid gap-4">
                        <div className="space-y-2">
                          <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Title</Label>
                          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Project title" />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Brief</Label>
                          <Textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Describe the story, campaign, or content you want to build."
                            className="min-h-[220px]"
                          />
                        </div>
                        <div className="grid gap-4 md:grid-cols-2">
                          <div className="space-y-2">
                            <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Genre</Label>
                            <Input value={genre} onChange={(e) => setGenre(e.target.value)} />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Style</Label>
                            <Input value={style} onChange={(e) => setStyle(e.target.value)} />
                          </div>
                        </div>
                      </div>
                    </section>
                  )}

                  {step === "format" && (
                    <section className="rounded-[22px] border border-border bg-white p-5">
                      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        <Video className="h-3.5 w-3.5 text-[color:#083300]" />
                        Format
                      </div>
                      <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                          <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Episodes</Label>
                          <Input type="number" min={1} max={5} value={episodes} onChange={(e) => setEpisodes(Number(e.target.value))} />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Scenes per episode</Label>
                          <Input type="number" min={3} max={10} value={scenes} onChange={(e) => setScenes(Number(e.target.value))} />
                        </div>
                      </div>
                      <div className="mt-6">
                        <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Aspect ratio</div>
                        <div className="mt-3 grid gap-2 sm:grid-cols-3">
                          {(["16:9", "9:16", "1:1"] as const).map((ratio) => (
                            <button
                              key={ratio}
                              type="button"
                              onClick={() => setFrameRatio(ratio)}
                              className={`rounded-[16px] border px-4 py-4 text-left transition ${
                                frameRatio === ratio
                                  ? "border-[color:#083300] bg-[color:#f5ffd8] text-[color:#083300]"
                                  : "border-border bg-white text-foreground hover:bg-muted/40"
                              }`}
                            >
                              <div className="text-sm font-semibold">{ratio}</div>
                              <div className="mt-1 text-xs leading-5 text-muted-foreground">
                                {ratio === "16:9" ? "Landscape and product demos" : ratio === "9:16" ? "Vertical social delivery" : "Square preview and social crop"}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    </section>
                  )}

                  {step === "refs" && (
                    <section className="space-y-4 rounded-[22px] border border-border bg-white p-5">
                      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        <Upload className="h-3.5 w-3.5 text-[color:#083300]" />
                        Reference library
                      </div>
                      <ReferenceUploadSection
                        label="Style references"
                        description="Mood boards, lighting refs, color language, or composition examples."
                        items={styleRefs}
                        disabled={uploading}
                        onUpload={(files) => uploadFiles(files, setStyleRefs)}
                        onRemove={(url) => setStyleRefs((prev) => prev.filter((item) => item.url !== url))}
                      />
                      <ReferenceUploadSection
                        label="Character references"
                        description="Main character refs so the first generation has a strong identity anchor."
                        items={characterRefs}
                        disabled={uploading}
                        onUpload={(files) => uploadFiles(files, setCharacterRefs)}
                        onRemove={(url) => setCharacterRefs((prev) => prev.filter((item) => item.url !== url))}
                      />
                      <ReferenceUploadSection
                        label="Scene references"
                        description="Environment refs and scene-specific examples for production continuity."
                        items={sceneRefs}
                        disabled={uploading}
                        onUpload={(files) => uploadFiles(files, setSceneRefs)}
                        onRemove={(url) => setSceneRefs((prev) => prev.filter((item) => item.url !== url))}
                      />
                    </section>
                  )}

                  {step === "review" && (
                    <section className="rounded-[22px] border border-border bg-white p-5">
                      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        <Sparkles className="h-3.5 w-3.5 text-[color:#083300]" />
                        Review
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <div className="rounded-[16px] border border-border bg-muted/30 p-4">
                          <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Title</div>
                          <div className="mt-1 text-sm font-semibold text-foreground">{title || "Untitled production"}</div>
                        </div>
                        <div className="rounded-[16px] border border-border bg-muted/30 p-4">
                          <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Workflow</div>
                          <div className="mt-1 text-sm font-semibold text-foreground">{preset.label}</div>
                        </div>
                        <div className="rounded-[16px] border border-border bg-muted/30 p-4">
                          <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Format</div>
                          <div className="mt-1 text-sm font-semibold text-foreground">{frameRatio}</div>
                        </div>
                        <div className="rounded-[16px] border border-border bg-muted/30 p-4">
                          <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Scenes</div>
                          <div className="mt-1 text-sm font-semibold text-foreground">{episodes} episodes / {scenes} scenes</div>
                        </div>
                      </div>
                      <div className="mt-4 rounded-[16px] border border-border bg-muted/30 p-4 text-sm leading-6 text-muted-foreground">
                        {prompt || "Add a brief to generate the production summary."}
                      </div>
                    </section>
                  )}
                </div>

                <aside className="space-y-4">
                  <div className="rounded-[22px] border border-border bg-muted/20 p-5">
                    <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Production guide</div>
                    <div className="mt-3 space-y-3 text-sm leading-6 text-foreground">
                      <div className="flex items-start gap-3">
                        <div className="mt-1 h-2 w-2 rounded-full bg-[color:#96ff1a]" />
                        Keep the brief concise and specific.
                      </div>
                      <div className="flex items-start gap-3">
                        <div className="mt-1 h-2 w-2 rounded-full bg-[color:#96ff1a]" />
                        Add character refs before the first render.
                      </div>
                      <div className="flex items-start gap-3">
                        <div className="mt-1 h-2 w-2 rounded-full bg-[color:#96ff1a]" />
                        Choose the frame ratio before approval.
                      </div>
                    </div>
                  </div>

                  <div className="rounded-[22px] border border-border bg-white p-5">
                    <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Current counts</div>
                    <div className="mt-4 space-y-3 text-sm text-foreground">
                      <div className="flex items-center justify-between gap-4">
                        <span>Style refs</span>
                        <span className="text-muted-foreground">{styleRefs.length}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span>Character refs</span>
                        <span className="text-muted-foreground">{characterRefs.length}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span>Scene refs</span>
                        <span className="text-muted-foreground">{sceneRefs.length}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span>Estimated prep</span>
                        <span className="text-muted-foreground">{estimatedMinutes} min</span>
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
