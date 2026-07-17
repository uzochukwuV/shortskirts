import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useRoute } from "wouter";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Loader2,
  Lock,
  MessageSquareText,
  RefreshCw,
  Send,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  Video,
  WandSparkles,
} from "lucide-react";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { api, Character, HistoryEntry, Scene, Story } from "@/lib/api";

type ChatMessage = {
  role: "assistant" | "user";
  text: string;
};

function storyTone(status: Story["status"]) {
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

function sceneTone(status: string, approval: string) {
  if (approval === "approved") return "border-emerald-200 bg-emerald-50";
  if (approval === "rejected") return "border-rose-200 bg-rose-50";
  if (status === "running") return "border-[color:#96ff1a] bg-[color:#f5ffd8]";
  return "border-border bg-white";
}

function formatShortDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function SceneTile({
  scene,
  active,
  onClick,
}: {
  scene: Scene;
  active: boolean;
  onClick: () => void;
}) {
  const media = scene.image_url || scene.clip_url || scene.video_url;
  const kind = scene.media_kind || (scene.image_url ? "image" : "video");

  return (
    <button
      type="button"
      onClick={onClick}
      className={`group min-w-[180px] max-w-[180px] shrink-0 snap-start overflow-hidden rounded-[16px] border text-left transition-all ${
        active ? "border-[color:#083300] shadow-[0_0_0_1px_rgba(8,51,0,0.14)]" : "border-border hover:border-[color:#96ff1a]"
      }`}
    >
      <div className="relative aspect-[16/10] bg-[color:#121212]">
        {media ? (
          kind === "image" ? (
            <img src={media} alt={scene.title || `Scene ${scene.scene_number}`} className="h-full w-full object-cover" />
          ) : (
            <video src={media} className="h-full w-full object-cover" muted playsInline preload="metadata" />
          )
        ) : (
          <div className="flex h-full items-center justify-center text-white/30">
            <Video className="h-8 w-8" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
        <div className="absolute left-2 top-2 rounded-[9999px] border border-white/10 bg-black/50 px-2 py-0.5 text-[10px] text-white">
          S{scene.scene_number}
        </div>
        <div className="absolute bottom-2 left-2 right-2">
          <div className="line-clamp-2 text-[12px] font-medium text-white">{scene.title || `Scene ${scene.scene_number}`}</div>
        </div>
      </div>
    </button>
  );
}

function HistoryLine({ entry }: { entry: HistoryEntry }) {
  return (
    <div className="flex items-start gap-3 rounded-[14px] border border-border bg-white px-3 py-2">
      <div className="mt-1 h-2 w-2 rounded-full bg-[color:#96ff1a]" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <div className="truncate text-xs font-medium text-foreground">{entry.event_type}</div>
          <div className="text-[10px] text-muted-foreground">v{entry.revision}</div>
        </div>
        <div className="mt-1 text-[11px] text-muted-foreground">
          {formatShortDate(entry.created_at)}
        </div>
      </div>
    </div>
  );
}

export default function StoryDetail() {
  const [, params] = useRoute("/stories/:id");
  const [, setLocation] = useLocation();
  const qc = useQueryClient();
  const id = params?.id || "";
  const [selectedSceneId, setSelectedSceneId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState("");

  const { data: story, isLoading: storyLoading } = useQuery({
    queryKey: ["story", id],
    queryFn: () => api.getStory(id),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === "generating" || query.state.data?.status === "checkpoint_review" ? 5000 : false,
  });

  const { data: characters = [] } = useQuery({
    queryKey: ["characters", id],
    queryFn: () => api.getCharacters(id),
    enabled: !!id,
  });

  const { data: episodes = [] } = useQuery({
    queryKey: ["episodes", id],
    queryFn: () => api.getEpisodes(id),
    enabled: !!id,
    refetchInterval: story?.status === "generating" || story?.status === "checkpoint_review" ? 5000 : false,
  });

  const { data: storyHistory = [] } = useQuery({
    queryKey: ["story-history", id],
    queryFn: () => api.getStoryHistory(id),
    enabled: !!id,
  });

  const { data: checkpoints = [] } = useQuery({
    queryKey: ["checkpoints", id],
    queryFn: () => api.getStoryCheckpoints(id),
    enabled: !!id,
    refetchInterval: story?.status === "checkpoint_review" ? 5000 : false,
  });

  const allScenes = useMemo(() => episodes.flatMap((episode) => episode.scenes ?? []), [episodes]);
  const selectedScene = useMemo(
    () => allScenes.find((scene) => scene.id === selectedSceneId) ?? allScenes[0] ?? null,
    [allScenes, selectedSceneId],
  );

  useEffect(() => {
    if (!selectedSceneId && allScenes.length > 0) {
      setSelectedSceneId(allScenes[0].id);
    }
  }, [allScenes, selectedSceneId]);

  const { data: sceneHistory = [] } = useQuery({
    queryKey: ["scene-history", selectedScene?.id],
    queryFn: () => api.getSceneHistory(selectedScene!.id),
    enabled: !!selectedScene?.id,
  });

  const latestAudioCheckpoint = useMemo(
    () =>
      [...checkpoints]
        .filter((checkpoint) => checkpoint.narration_audio_url || checkpoint.audio_status === "completed")
        .sort((a, b) => (a.batch_number || 0) - (b.batch_number || 0))
        .slice(-1)[0] ?? null,
    [checkpoints],
  );

  const activeCheckpoint = checkpoints.find((checkpoint) => checkpoint.status === "pending_review") ?? null;
  const checkpointAudioReady =
    !activeCheckpoint?.audio_status ||
    activeCheckpoint.audio_status === "completed" ||
    activeCheckpoint.audio_status === "failed";

  const approveOutline = useMutation({
    mutationFn: () => api.approveOutline(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["story", id] }),
  });

  const generateStory = useMutation({
    mutationFn: () => api.generateStory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["episodes", id] });
    },
  });

  const approveCheckpoint = useMutation({
    mutationFn: (checkpointId: string) => api.approveCheckpoint(id, checkpointId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["checkpoints", id] });
    },
  });

  const approveScene = useMutation({
    mutationFn: (sceneId: string) => api.approveScene(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }),
  });

  const rejectScene = useMutation({
    mutationFn: (sceneId: string) => api.rejectScene(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }),
  });

  const lockScene = useMutation({
    mutationFn: (sceneId: string) => api.lockScene(sceneId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }),
  });

  const regenerateScene = useMutation({
    mutationFn: (sceneId: string) => api.regenerateScene(sceneId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", id] });
    },
  });

  useEffect(() => {
    if (!story || messages.length > 0) return;
    setMessages([
      {
        role: "assistant",
        text: `Console ready for ${story.title}. Select a scene, approve the outline, or regenerate the current frame.`,
      },
    ]);
  }, [story, messages.length]);

  const sendMessage = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    const lower = trimmed.toLowerCase();

    if (lower.includes("approve outline") && story?.status === "draft") {
      approveOutline.mutate();
      setMessages((prev) => [...prev, { role: "assistant", text: "Outline approval queued." }]);
      return;
    }
    if (lower.includes("approve checkpoint") && activeCheckpoint?.id && checkpointAudioReady) {
      approveCheckpoint.mutate(activeCheckpoint.id);
      setMessages((prev) => [...prev, { role: "assistant", text: "Checkpoint approval queued." }]);
      return;
    }
    if (lower.includes("generate story") || lower === "generate") {
      generateStory.mutate();
      setMessages((prev) => [...prev, { role: "assistant", text: "Story generation queued." }]);
      return;
    }
    if (lower.includes("approve scene") && selectedScene) {
      approveScene.mutate(selectedScene.id);
      setMessages((prev) => [...prev, { role: "assistant", text: `Scene ${selectedScene.scene_number} approval queued.` }]);
      return;
    }
    if (lower.includes("reject scene") && selectedScene) {
      rejectScene.mutate(selectedScene.id);
      setMessages((prev) => [...prev, { role: "assistant", text: `Scene ${selectedScene.scene_number} rejection queued.` }]);
      return;
    }
    if (lower.includes("regenerate") && selectedScene) {
      regenerateScene.mutate(selectedScene.id);
      setMessages((prev) => [...prev, { role: "assistant", text: `Scene ${selectedScene.scene_number} regeneration queued.` }]);
      return;
    }

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        text: selectedScene
          ? `Focused on ${selectedScene.title || `Scene ${selectedScene.scene_number}`}. I can approve, regenerate, or lock the current version.`
          : "Pick a scene to inspect it here.",
      },
    ]);
  };

  const onSubmitPrompt = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    sendMessage(prompt);
    setPrompt("");
  };

  const currentMedia = selectedScene?.image_url || selectedScene?.clip_url || selectedScene?.video_url;
  const currentKind = selectedScene?.media_kind || (selectedScene?.image_url ? "image" : "video");

  if (storyLoading) {
    return (
      <Layout>
        <div className="min-h-[60vh] bg-white" />
      </Layout>
    );
  }

  if (!story) {
    return (
      <Layout>
        <div className="mx-auto max-w-[1200px] px-4 py-20 md:px-6">
          <div className="rounded-[16px] border border-border bg-white p-8 text-sm text-muted-foreground">
            Story not found.
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="bg-white">
        <section className="border-b border-border">
          <div className="mx-auto flex max-w-[1200px] flex-col gap-4 px-4 py-8 md:px-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Link href="/dashboard">
                  <Button variant="ghost" size="sm" className="px-2">
                    <ArrowLeft className="h-4 w-4" />
                    Dashboard
                  </Button>
                </Link>
                <div className="min-w-0">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                    {story.workflow_type}
                  </div>
                  <h1 className="truncate font-display text-[40px] leading-[1] tracking-[-0.04em] text-foreground md:text-[54px]">
                    {story.title}
                  </h1>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className={`inline-flex items-center rounded-[9999px] border px-3 py-1.5 text-[11px] font-medium ${storyTone(story.status)}`}>
                  {story.status}
                </div>
                {story.status === "draft" && (
                  <Button variant="lime" onClick={() => approveOutline.mutate()} disabled={approveOutline.isPending}>
                    {approveOutline.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                    Approve outline
                  </Button>
                )}
                {story.status === "approved" && (
                  <Button variant="lime" onClick={() => generateStory.mutate()} disabled={generateStory.isPending}>
                    {generateStory.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
                    Generate
                  </Button>
                )}
                {activeCheckpoint && (
                  <Button
                    variant="outline"
                    onClick={() => approveCheckpoint.mutate(activeCheckpoint.id)}
                    disabled={!checkpointAudioReady || approveCheckpoint.isPending}
                  >
                    {approveCheckpoint.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                    Approve checkpoint
                  </Button>
                )}
              </div>
            </div>

            <p className="max-w-3xl text-[16px] leading-7 text-muted-foreground">
              {story.prompt}
            </p>

            <div className="flex flex-wrap gap-2">
              <Badge className="border-border bg-muted text-foreground">{story.workflow_version || "v1"}</Badge>
              <Badge className="border-border bg-muted text-foreground">{story.generation_version || "v1"}</Badge>
              <Badge className="border-border bg-muted text-foreground">{story.approval_status}</Badge>
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-[1200px] gap-6 px-4 py-8 md:px-6 lg:grid-cols-[360px_1fr]">
          <aside className="space-y-4">
            <div className="rounded-[16px] border border-border bg-[color:#121212] p-5 text-white">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-white/60">
                <MessageSquareText className="h-3.5 w-3.5 text-[color:#96ff1a]" />
                AI chat
              </div>

              <div className="mt-4 flex h-[460px] flex-col gap-3 overflow-y-auto pr-1">
                {messages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`max-w-[90%] rounded-[16px] px-4 py-3 text-sm leading-6 ${
                      message.role === "assistant"
                        ? "bg-white/8 border border-white/10 text-white"
                        : "ml-auto bg-[color:#96ff1a] text-[color:#083300]"
                    }`}
                  >
                    {message.text}
                  </div>
                ))}
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  "approve outline",
                  "generate story",
                  "approve scene",
                  "regenerate",
                ].map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => {
                      setPrompt(chip);
                      sendMessage(chip);
                    }}
                    className="rounded-[9999px] border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-white/70 transition-colors hover:bg-white/10"
                  >
                    {chip}
                  </button>
                ))}
              </div>

              <form onSubmit={onSubmitPrompt} className="mt-4 flex gap-2">
                <Input
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Ask the console to act"
                  className="border-white/10 bg-white/5 text-white placeholder:text-white/40"
                />
                <Button type="submit" variant="lime" className="shrink-0">
                  <Send className="h-4 w-4" />
                </Button>
              </form>
            </div>

            <div className="rounded-[16px] border border-border bg-white p-5">
              <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">History</div>
              <div className="mt-3 space-y-2">
                {storyHistory.slice(0, 6).map((entry) => (
                  <HistoryLine key={entry.id} entry={entry} />
                ))}
              </div>
            </div>

            <div className="rounded-[16px] border border-border bg-white p-5">
              <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Cast</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {characters.length > 0 ? characters.slice(0, 8).map((character: Character) => (
                  <div
                    key={character.id}
                    className="rounded-[9999px] border border-border bg-muted px-3 py-1.5 text-[11px] text-foreground"
                  >
                    {character.name}
                  </div>
                )) : (
                  <div className="text-sm text-muted-foreground">No characters yet.</div>
                )}
              </div>
            </div>
          </aside>

          <div className="space-y-5">
            <div className="rounded-[16px] border border-border bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Generated parts</div>
                  <div className="mt-1 text-sm text-foreground">
                    {allScenes.length} scenes available
                  </div>
                </div>
                <div className="text-xs text-muted-foreground">
                  {selectedScene ? `Selected scene ${selectedScene.scene_number}` : "No scene selected"}
                </div>
              </div>
              <div className="mt-4 flex gap-3 overflow-x-auto pb-1 [scrollbar-width:none]">
                {allScenes.map((scene) => (
                  <SceneTile
                    key={scene.id}
                    scene={scene}
                    active={scene.id === selectedScene?.id}
                    onClick={() => setSelectedSceneId(scene.id)}
                  />
                ))}
              </div>
            </div>

            <div className="rounded-[16px] border border-border bg-[color:#121212] p-4 text-white">
              <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-4">
                <div className="min-w-0">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">
                    {selectedScene ? `Episode ${episodes.find((ep) => ep.scenes?.some((scene) => scene.id === selectedScene.id))?.episode_number ?? ""}` : "Preview"}
                  </div>
                  <h2 className="mt-1 truncate text-[20px] font-semibold text-white">
                    {selectedScene?.title || "Select a scene"}
                  </h2>
                  <p className="mt-1 max-w-3xl text-sm leading-6 text-white/65">
                    {selectedScene?.description || story.prompt}
                  </p>
                </div>

                {selectedScene && (
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button
                      size="sm"
                      variant="lime"
                      onClick={() => approveScene.mutate(selectedScene.id)}
                      disabled={approveScene.isPending || selectedScene.approval_status === "approved"}
                    >
                      {approveScene.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ThumbsUp className="h-4 w-4" />}
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => rejectScene.mutate(selectedScene.id)}
                      disabled={rejectScene.isPending || selectedScene.approval_status === "rejected"}
                    >
                      {rejectScene.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ThumbsDown className="h-4 w-4" />}
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => regenerateScene.mutate(selectedScene.id)}
                      disabled={regenerateScene.isPending}
                    >
                      {regenerateScene.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                      Regenerate
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => lockScene.mutate(selectedScene.id)}
                      disabled={lockScene.isPending || !!selectedScene.locked}
                    >
                      <Lock className="h-4 w-4" />
                      Lock
                    </Button>
                  </div>
                )}
              </div>

              <div className="mt-4 overflow-hidden rounded-[14px] border border-white/10 bg-black">
                {currentMedia ? (
                  currentKind === "image" ? (
                    <img
                      src={currentMedia}
                      alt={selectedScene?.title || "Selected scene"}
                      className="aspect-video w-full object-contain bg-black"
                    />
                  ) : (
                    <video
                      src={currentMedia}
                      className="aspect-video w-full object-contain bg-black"
                      controls
                      playsInline
                      muted
                      preload="metadata"
                    />
                  )
                ) : (
                  <div className="flex aspect-video items-center justify-center">
                    <div className="text-center text-white/40">
                      <Video className="mx-auto h-10 w-10" />
                      <div className="mt-2 text-sm">No media on this scene yet</div>
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-4">
                {[
                  { label: "Version", value: selectedScene?.generation_version || story.generation_version || "v1" },
                  { label: "Image model", value: selectedScene?.image_model || "-" },
                  { label: "Edit model", value: selectedScene?.edit_model || "-" },
                  { label: "Regen count", value: selectedScene?.regeneration_count ?? 0 },
                ].map((item) => (
                  <div key={item.label} className="rounded-[14px] border border-white/10 bg-white/5 px-4 py-3">
                    <div className="text-[10px] uppercase tracking-[0.16em] text-white/45">{item.label}</div>
                    <div className="mt-1 text-sm text-white">{item.value}</div>
                  </div>
                ))}
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_320px]">
                <div className="rounded-[14px] border border-white/10 bg-white/5 p-4">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-white/55">Selected scene history</div>
                  <div className="mt-3 space-y-2">
                    {sceneHistory.slice(0, 4).map((entry) => (
                      <div
                        key={entry.id}
                        className="flex items-start justify-between gap-3 rounded-[12px] border border-white/10 bg-black/20 px-3 py-2 text-sm text-white/80"
                      >
                        <span className="truncate">{entry.event_type}</span>
                        <span className="text-[10px] text-white/40">v{entry.revision}</span>
                      </div>
                    ))}
                    {!sceneHistory.length && (
                      <div className="text-sm text-white/45">No scene history yet.</div>
                    )}
                  </div>
                </div>

                <div className="rounded-[14px] border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-white/55">
                    <Clock3 className="h-3.5 w-3.5" />
                    Audio
                  </div>
                  {latestAudioCheckpoint?.narration_audio_url ? (
                    <div className="mt-3 space-y-3">
                      <audio controls className="w-full" src={latestAudioCheckpoint.narration_audio_url} />
                      <div className="text-sm text-white/80">
                        {latestAudioCheckpoint.narration_text || "Narration is available for this batch."}
                      </div>
                      <div className="flex flex-wrap gap-2 text-[11px] text-white/55">
                        <span className="rounded-[9999px] border border-white/10 bg-white/5 px-2.5 py-1">
                          batch {latestAudioCheckpoint.batch_number}
                        </span>
                        <span className="rounded-[9999px] border border-white/10 bg-white/5 px-2.5 py-1">
                          {latestAudioCheckpoint.narration_voice || "voice"}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-3 text-sm text-white/45">
                      No audio has been generated yet.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}
