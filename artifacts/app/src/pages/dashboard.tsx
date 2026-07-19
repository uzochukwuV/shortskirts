import { useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation } from "wouter";
import {
  ArrowRight,
  CheckCircle2,
  Clapperboard,
  Clock,
  FolderKanban,
  Gauge,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  Upload,
  Video,
} from "lucide-react";
import { Layout } from "@/components/layout";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, Story, WorkflowType } from "@/lib/api";

type WorkflowPreset = {
  id: WorkflowType;
  label: string;
  description: string;
  episodes: number;
  scenes: number;
  genre: string;
  style: string;
};

const WORKFLOWS: WorkflowPreset[] = [
  { id: "creator_series", label: "Creator series", description: "Serialized episodes with recurring cast and approvals.", episodes: 3, scenes: 5, genre: "action", style: "anime" },
  { id: "narrated_image_story", label: "Narrated image story", description: "Image-led scenes with voice-over and continuity passes.", episodes: 1, scenes: 6, genre: "drama", style: "anime" },
  { id: "brand_campaign", label: "Brand campaign", description: "Fast ad concepts with product framing and CTA.", episodes: 1, scenes: 3, genre: "slice-of-life", style: "modern-anime" },
  { id: "social_short", label: "Social short", description: "Hook-heavy short form for vertical feeds.", episodes: 1, scenes: 4, genre: "action", style: "modern-anime" },
  { id: "educational", label: "Educational explainer", description: "Structured lessons with a guided visual sequence.", episodes: 1, scenes: 5, genre: "slice-of-life", style: "anime" },
  { id: "game_lore", label: "Game lore", description: "Worldbuilding trailers and lore teasers.", episodes: 1, scenes: 4, genre: "fantasy", style: "anime" },
];

function statusTone(status: Story["status"]) {
  switch (status) {
    case "draft":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "approved":
      return "border-border bg-muted text-foreground";
    case "generating":
      return "border-[color:#96ff1a] bg-[color:#f5ffd8] text-[color:#083300]";
    case "checkpoint_review":
      return "border-[color:#96ff1a] bg-white text-[color:#083300]";
    case "completed":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    default:
      return "border-border bg-white text-foreground";
  }
}

function statusLabel(status: Story["status"]) {
  return status === "ready" ? "completed" : status;
}

function StoryCard({ story }: { story: Story }) {
  return (
    <Link href={`/stories/${story.id}`} className="block">
      <article className="group rounded-[16px] border border-border bg-white p-5 transition-all hover:border-[color:#083300]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className={`inline-flex items-center rounded-[9999px] border px-2.5 py-1 text-[11px] font-medium ${statusTone(story.status)}`}>
              {statusLabel(story.status)}
            </div>
            <h3 className="mt-3 truncate text-[20px] font-display leading-[1] tracking-[-0.04em] text-foreground">
              {story.title}
            </h3>
          </div>
          <div className="rounded-[9999px] border border-border bg-muted px-2.5 py-1 text-[11px] text-muted-foreground">
            {story.workflow_type}
          </div>
        </div>

        <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">{story.prompt}</p>

        <div className="mt-5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
          <span className="rounded-[9999px] border border-border bg-muted px-2.5 py-1">
            {story.workflow_version || "v1"}
          </span>
          <span className="rounded-[9999px] border border-border bg-muted px-2.5 py-1">
            {story.generation_version || "v1"}
          </span>
          <span className="rounded-[9999px] border border-border bg-muted px-2.5 py-1">
            {story.approval_status}
          </span>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-border pt-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5" />
            {new Date(story.created_at).toLocaleDateString()}
          </span>
          <span className="inline-flex items-center gap-1 text-foreground group-hover:translate-x-0.5 transition-transform">
            Open
            <ArrowRight className="h-3.5 w-3.5" />
          </span>
        </div>
      </article>
    </Link>
  );
}

type RefAsset = {
  url: string;
  name: string;
};

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
    <div className="space-y-3 rounded-[16px] border border-border bg-muted/30 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-foreground">{label}</div>
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
        {items.length > 0 ? items.map((item) => (
          <div key={item.url} className="group relative overflow-hidden rounded-[12px] border border-border bg-white">
            <img src={item.url} alt={item.name} className="h-24 w-full object-cover" />
            <button
              type="button"
              onClick={() => onRemove(item.url)}
              className="absolute right-1 top-1 rounded-full border border-white/20 bg-black/60 p-1 text-white opacity-0 transition-opacity group-hover:opacity-100"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        )) : (
          <div className="col-span-3 rounded-[12px] border border-dashed border-border bg-white px-3 py-4 text-xs text-muted-foreground">
            No images uploaded yet.
          </div>
        )}
      </div>
    </div>
  );
}

function CreateProductionDialog({ onCreated }: { onCreated: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowType>("creator_series");
  const preset = WORKFLOWS.find((item) => item.id === selectedWorkflow) ?? WORKFLOWS[0];
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [genre, setGenre] = useState(preset.genre);
  const [style, setStyle] = useState(preset.style);
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
      setTitle("");
      setPrompt("");
      setSelectedWorkflow("creator_series");
      setGenre(WORKFLOWS[0].genre);
      setStyle(WORKFLOWS[0].style);
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
    setEpisodes(next.episodes);
    setScenes(next.scenes);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="lime">
          <Plus className="h-4 w-4" />
          New production
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-[980px] border-border bg-white p-0">
        <div className="grid gap-0 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="border-b border-border bg-[color:#121212] p-6 text-white lg:border-b-0 lg:border-r">
            <div className="inline-flex items-center gap-2 rounded-[9999px] border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-white/70">
              <Sparkles className="h-3.5 w-3.5 text-[color:#96ff1a]" />
              Brief to production
            </div>
            <DialogTitle className="mt-5 font-display text-[40px] leading-[1] tracking-[-0.04em] text-white">
              Build a new series.
            </DialogTitle>
            <p className="mt-4 max-w-md text-sm leading-6 text-white/70">
              Pick the workflow, define the brief, and send it into the pipeline.
            </p>

            <div className="mt-8 space-y-2">
              {WORKFLOWS.map((workflow) => (
                <button
                  key={workflow.id}
                  type="button"
                  onClick={() => setWorkflow(workflow.id)}
                  className={`w-full rounded-[16px] border px-4 py-3 text-left transition-colors ${
                    selectedWorkflow === workflow.id
                      ? "border-[color:#96ff1a] bg-white text-[color:#083300]"
                      : "border-white/10 bg-white/5 text-white hover:bg-white/10"
                  }`}
                >
                  <div className="text-sm font-medium">{workflow.label}</div>
                  <div className={`mt-1 text-xs leading-5 ${selectedWorkflow === workflow.id ? "text-[color:#083300]/70" : "text-white/55"}`}>
                    {workflow.description}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="p-6">
            <div className="grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Title</Label>
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Project title"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Genre</Label>
                  <Input value={genre} onChange={(e) => setGenre(e.target.value)} />
                </div>
              </div>

                <div className="space-y-2">
                  <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Brief</Label>
                  <Textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Describe the story, campaign, or content you want to build."
                    className="min-h-[180px]"
                  />
                </div>

              <div className="grid gap-4">
              <ReferenceUploadSection
                label="Style references"
                description="Upload mood boards, lighting refs, color language, or composition examples."
                items={styleRefs}
                disabled={uploading}
                onUpload={(files) => uploadFiles(files, setStyleRefs)}
                onRemove={(url) => setStyleRefs((prev) => prev.filter((item) => item.url !== url))}
              />
              <ReferenceUploadSection
                label="Character references"
                description="Upload main character refs before generation starts so consistency has a base."
                items={characterRefs}
                disabled={uploading}
                onUpload={(files) => uploadFiles(files, setCharacterRefs)}
                onRemove={(url) => setCharacterRefs((prev) => prev.filter((item) => item.url !== url))}
              />
              <ReferenceUploadSection
                label="Scene references"
                description="Upload scene-specific refs you want the generator to carry into production."
                items={sceneRefs}
                disabled={uploading}
                onUpload={(files) => uploadFiles(files, setSceneRefs)}
                onRemove={(url) => setSceneRefs((prev) => prev.filter((item) => item.url !== url))}
              />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Style</Label>
                  <Input value={style} onChange={(e) => setStyle(e.target.value)} />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Episodes</Label>
                    <Input
                      type="number"
                      min={1}
                      max={5}
                      value={episodes}
                      onChange={(e) => setEpisodes(Number(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Scenes</Label>
                    <Input
                      type="number"
                      min={3}
                      max={10}
                      value={scenes}
                      onChange={(e) => setScenes(Number(e.target.value))}
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
                <div className="text-xs text-muted-foreground">
                  The outline is created first, then generation starts after approval.
                </div>
                <Button
                  variant="lime"
                  disabled={!title.trim() || !prompt.trim() || create.isPending || uploading}
                  onClick={() => create.mutate()}
                >
                  {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Clapperboard className="h-4 w-4" />}
                  Create production
                </Button>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const { data: stories = [], isLoading } = useQuery({
    queryKey: ["stories"],
    queryFn: api.getStories,
    refetchInterval: (query) =>
      query.state.data?.some((story: Story) => story.status === "generating" || story.status === "checkpoint_review")
        ? 6000
        : false,
  });

  const metrics = useMemo(() => {
    const total = stories.length;
    const drafts = stories.filter((story) => story.status === "draft").length;
    const active = stories.filter((story) => story.status === "generating" || story.status === "checkpoint_review").length;
    const complete = stories.filter((story) => story.status === "completed" || story.status === "ready").length;
    return { total, drafts, active, complete };
  }, [stories]);

  const activeStories = stories
    .filter((story) => story.status === "generating" || story.status === "checkpoint_review")
    .slice(0, 4);

  const recentStories = stories.slice(0, 6);

  return (
    <Layout>
      <div className="bg-white">
        <section className="space-y-6">
          <PageHeader
            eyebrow="Studio index"
            title="Production dashboard for stories that already exist in the backend."
            description="Briefs, approvals, version history, and render state are all exposed here. Open a story to work the console."
            actions={<CreateProductionDialog onCreated={(id) => setLocation(`/stories/${id}`)} />}
            stats={[
              { label: "Total productions", value: String(metrics.total), hint: "All stories in the workspace." },
              { label: "Drafts", value: String(metrics.drafts), hint: "Awaiting approval or edits." },
              { label: "Active", value: String(metrics.active), hint: "Currently generating." },
              { label: "Completed", value: String(metrics.complete), hint: "Ready for review." },
            ]}
          />
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-4">
            <div className="flex items-end justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Recent productions</div>
                <h2 className="mt-2 font-display text-[40px] leading-[1] tracking-[-0.04em] text-foreground">
                  Open a story to enter the console.
                </h2>
              </div>
              <div className="text-sm text-muted-foreground">
                {isLoading ? "Loading..." : `${recentStories.length} shown`}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {recentStories.length > 0 ? (
                recentStories.map((story) => <StoryCard key={story.id} story={story} />)
              ) : (
                <div className="rounded-[16px] border border-dashed border-border bg-muted/30 p-8 text-sm text-muted-foreground md:col-span-2">
                  No productions yet. Create one from the studio button.
                </div>
              )}
            </div>
          </div>

          <aside className="space-y-4">
            <div className="rounded-[16px] border border-border bg-[color:#121212] p-5 text-white">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-white/60">
                <Gauge className="h-3.5 w-3.5 text-[color:#96ff1a]" />
                Live queue
              </div>
              <div className="mt-3 space-y-3">
                {activeStories.length > 0 ? activeStories.map((story) => (
                  <button
                    key={story.id}
                    type="button"
                    onClick={() => setLocation(`/stories/${story.id}`)}
                    className="w-full rounded-[14px] border border-white/10 bg-white/5 px-4 py-3 text-left transition-colors hover:bg-white/10"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-white">{story.title}</div>
                        <div className="mt-1 text-xs text-white/60">{story.workflow_type}</div>
                      </div>
                      <Badge className="border-0 bg-[color:#96ff1a] text-[color:#083300]">
                        {statusLabel(story.status)}
                      </Badge>
                    </div>
                  </button>
                )) : (
                  <div className="rounded-[14px] border border-white/10 bg-white/5 px-4 py-6 text-sm text-white/60">
                    No active jobs.
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[16px] border border-border bg-white p-5">
              <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Session notes</div>
              <div className="mt-3 space-y-3 text-sm leading-6 text-foreground">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                  <span>Scene and checkpoint versioning is already exposed.</span>
                </div>
                <div className="flex items-start gap-3">
                  <Video className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                  <span>Open a story to see the video console with scene boxes and narration.</span>
                </div>
                <div className="flex items-start gap-3">
                  <Sparkles className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                  <span>Create the next production from the button above.</span>
                </div>
              </div>
            </div>
          </aside>
        </section>
      </div>
    </Layout>
  );
}
