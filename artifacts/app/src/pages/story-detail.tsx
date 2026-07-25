import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { api } from "@/lib/api";
import {
  type AssistantTarget,
  type ConsoleWorkspace,
  MomoConsole,
} from "@/components/story-console/momo-console";

type ChatMessage = { role: "assistant" | "user"; text: string };

export default function StoryDetail() {
  const [, params] = useRoute("/stories/:id");
  const id = params?.id || "";
  const qc = useQueryClient();
  const [selectedSceneId, setSelectedSceneId] = useState("");
  const [activeWorkspace, setActiveWorkspace] = useState<ConsoleWorkspace>("canvas");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [assistantTarget, setAssistantTarget] = useState<AssistantTarget>("story");
  const [sceneRefUploading, setSceneRefUploading] = useState(false);
  const [assistantMessage, setAssistantMessage] = useState<string | null>(null);
  const [storyDraft, setStoryDraft] = useState<Record<string, any> | null>(null);
  const [sceneDraft, setSceneDraft] = useState<Record<string, any> | null>(null);

  const { data: story, isLoading: storyLoading } = useQuery({
    queryKey: ["story", id],
    queryFn: () => api.getStory(id),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.status === "generating" || query.state.data?.status === "checkpoint_review" ? 5000 : false),
  });
  const { data: characters = [] } = useQuery({ queryKey: ["characters", id], queryFn: () => api.getCharacters(id), enabled: !!id });
  const { data: episodes = [] } = useQuery({
    queryKey: ["episodes", id],
    queryFn: () => api.getEpisodes(id),
    enabled: !!id,
    refetchInterval: story?.status === "generating" || story?.status === "checkpoint_review" ? 5000 : false,
  });
  const { data: storyHistory = [] } = useQuery({ queryKey: ["story-history", id], queryFn: () => api.getStoryHistory(id), enabled: !!id });
  const { data: storyJobs = [] } = useQuery({
    queryKey: ["story-jobs", id],
    queryFn: () => api.getEntityJobs("story", id),
    enabled: !!id,
    refetchInterval: story?.status === "generating" || story?.status === "checkpoint_review" ? 3000 : false,
  });
  const { data: checkpoints = [] } = useQuery({
    queryKey: ["checkpoints", id],
    queryFn: () => api.getStoryCheckpoints(id),
    enabled: !!id,
    refetchInterval: story?.status === "checkpoint_review" ? 5000 : false,
  });

  const allScenes = useMemo(() => episodes.flatMap((episode) => episode.scenes ?? []), [episodes]);
  const selectedScene = useMemo(() => allScenes.find((scene) => scene.id === selectedSceneId) ?? allScenes[0] ?? null, [allScenes, selectedSceneId]);
  const selectedEpisode = useMemo(() => episodes.find((episode) => episode.scenes?.some((scene) => scene.id === selectedScene?.id)) ?? episodes[0], [episodes, selectedScene]);
  const latestStoryJob = useMemo(() => storyJobs[0] ?? null, [storyJobs]);
  const latestAudioCheckpoint = useMemo(
    () =>
      [...checkpoints]
        .filter((checkpoint) => checkpoint.narration_audio_url || checkpoint.audio_status === "completed")
        .sort((a, b) => (a.batch_number || 0) - (b.batch_number || 0))
        .slice(-1)[0] ?? null,
    [checkpoints],
  );

  useEffect(() => {
    if (!selectedSceneId && allScenes.length > 0) setSelectedSceneId(allScenes[0].id);
  }, [allScenes, selectedSceneId]);

  const { data: sceneHistory = [] } = useQuery({
    queryKey: ["scene-history", selectedScene?.id],
    queryFn: () => api.getSceneHistory(selectedScene!.id),
    enabled: !!selectedScene?.id,
  });

  const approveOutline = useMutation({
    mutationFn: () => api.approveOutline(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["story-history", id] });
    },
  });
  const generateStory = useMutation({
    mutationFn: () => api.generateStory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      qc.invalidateQueries({ queryKey: ["story-jobs", id] });
    },
  });
  const approveScene = useMutation({
    mutationFn: (sceneId: string) => api.approveScene(sceneId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      if (selectedScene?.id) qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
    },
  });
  const rejectScene = useMutation({
    mutationFn: (sceneId: string) => api.rejectScene(sceneId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      if (selectedScene?.id) qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
    },
  });
  const lockScene = useMutation({
    mutationFn: (sceneId: string) => api.lockScene(sceneId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      if (selectedScene?.id) qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
    },
  });
  const regenerateScene = useMutation({
    mutationFn: (sceneId: string) => api.regenerateScene(sceneId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      qc.invalidateQueries({ queryKey: ["story-jobs", id] });
      if (selectedScene?.id) qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
    },
  });
  const updateStory = useMutation({
    mutationFn: (patch: Record<string, any>) => api.updateStory(id, patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["story-history", id] });
      setStoryDraft(null);
    },
  });
  const updateScene = useMutation({
    mutationFn: ({ sceneId, patch }: { sceneId: string; patch: Record<string, any> }) => api.updateScene(sceneId, patch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      if (selectedScene?.id) qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
      setSceneDraft(null);
    },
  });
  const assist = useMutation({
    mutationFn: (payload: { instruction: string; target: AssistantTarget; scene_id?: string }) => api.assistStory(id, payload),
    onSuccess: (result) => {
      setAssistantMessage(result.message);
      if (result.target === "story") {
        setStoryDraft(result.story_patch || {});
        setSceneDraft(null);
      } else {
        setSceneDraft(result.scene_patch || {});
      }
      setMessages((prev) => [...prev, { role: "assistant", text: result.message }]);
    },
  });

  const sceneReferenceUrls = useMemo(() => {
    const raw = selectedScene?.state_snapshot?.reference_image_urls;
    return Array.isArray(raw) ? raw.filter((item): item is string => typeof item === "string" && item.length > 0) : [];
  }, [selectedScene]);

  const uploadSceneRefs = async (files: FileList | null) => {
    if (!selectedScene || !files?.length) return;
    setSceneRefUploading(true);
    try {
      const uploads = await Promise.all(Array.from(files).map(async (file) => (await api.uploadImage(file)).url));
      await api.updateSceneReferences(selectedScene.id, [...sceneReferenceUrls, ...uploads]);
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
    } finally {
      setSceneRefUploading(false);
    }
  };

  useEffect(() => {
    if (!story || messages.length > 0) return;
    setMessages([{ role: "assistant", text: `Workspace loaded for ${story.title}. Use the AI pane to revise the storyline or the selected scene text.` }]);
  }, [story, messages.length]);

  const sendAssistant = () => {
    const trimmed = prompt.trim();
    if (!trimmed || !story) return;
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setAssistantMessage(null);

    const lower = trimmed.toLowerCase();
    if (lower.includes("approve outline") && story.status === "draft") {
      approveOutline.mutate();
      setMessages((prev) => [...prev, { role: "assistant", text: "Outline approval queued." }]);
      setPrompt("");
      return;
    }
    if (lower.includes("generate")) {
      generateStory.mutate();
      setMessages((prev) => [...prev, { role: "assistant", text: "Generation queued." }]);
      setPrompt("");
      return;
    }
    if (assistantTarget === "scene" && !selectedScene) {
      setMessages((prev) => [...prev, { role: "assistant", text: "Select a scene before requesting a scene rewrite." }]);
      setPrompt("");
      return;
    }

    assist.mutate({
      instruction: trimmed,
      target: assistantTarget,
      scene_id: assistantTarget === "scene" ? selectedScene?.id : undefined,
    });
    setPrompt("");
  };

  const applyStoryDraft = () => {
    if (!storyDraft || !Object.keys(storyDraft).length) return;
    updateStory.mutate(storyDraft);
  };

  const applySceneDraft = () => {
    if (!selectedScene || !sceneDraft || !Object.keys(sceneDraft).length) return;
    updateScene.mutate({ sceneId: selectedScene.id, patch: sceneDraft });
  };

  if (storyLoading) return <div className="flex h-screen items-center justify-center bg-black text-zinc-400">Loading workspace...</div>;
  if (!story) return <div className="flex h-screen items-center justify-center bg-black text-zinc-200">Story not found.</div>;

  const currentMedia = selectedEpisode?.assembled_video_url || selectedScene?.image_url || selectedScene?.media_url || selectedScene?.clip_url || selectedScene?.video_url;
  const currentKind = selectedEpisode?.assembled_video_url
    ? "video"
    : selectedScene?.media_kind || (selectedScene?.image_url || selectedScene?.media_url ? "image" : "video");
  const expectedScenes = (story.num_episodes || 1) * (story.num_scenes || 0);
  const completedScenes = allScenes.filter((scene) => scene.status === "completed" || scene.status === "ready").length;
  const progressValue = latestStoryJob?.total_steps
    ? Math.min(100, Math.round((latestStoryJob.progress / latestStoryJob.total_steps) * 100))
    : expectedScenes
      ? Math.min(100, Math.round((completedScenes / expectedScenes) * 100))
      : 0;

  return (
    <MomoConsole
      story={story}
      episodes={episodes}
      scenes={allScenes}
      characters={characters}
      storyHistory={storyHistory}
      sceneHistory={sceneHistory}
      selectedScene={selectedScene}
      selectedEpisode={selectedEpisode}
      activeWorkspace={activeWorkspace}
      onChangeWorkspace={setActiveWorkspace}
      onSelectScene={setSelectedSceneId}
      onApproveOutline={() => approveOutline.mutate()}
      onGenerate={() => generateStory.mutate()}
      onApproveScene={(sceneId) => approveScene.mutate(sceneId)}
      onRejectScene={(sceneId) => rejectScene.mutate(sceneId)}
      onRegenerateScene={(sceneId) => regenerateScene.mutate(sceneId)}
      onLockScene={(sceneId) => lockScene.mutate(sceneId)}
      onSaveStoryEdit={(patch) => updateStory.mutate(patch)}
      onSaveSceneEdit={(sceneId, patch) => updateScene.mutate({ sceneId, patch })}
      currentMedia={currentMedia}
      currentKind={currentKind}
      latestJob={latestStoryJob}
      latestAudioCheckpoint={latestAudioCheckpoint}
      progressValue={progressValue}
      prompt={prompt}
      setPrompt={setPrompt}
      assistantTarget={assistantTarget}
      setAssistantTarget={setAssistantTarget}
      onSendAssistant={sendAssistant}
      messages={messages}
      referenceUrls={sceneReferenceUrls}
      onReferenceUpload={(files) => void uploadSceneRefs(files)}
      onReferenceRemove={(url) =>
        void (async () => {
          if (!selectedScene) return;
          await api.updateSceneReferences(selectedScene.id, sceneReferenceUrls.filter((item) => item !== url));
          qc.invalidateQueries({ queryKey: ["episodes", id] });
          qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
        })()
      }
      sceneRefUploading={sceneRefUploading}
      assistantMessage={assistantMessage}
      storyDraft={storyDraft}
      sceneDraft={sceneDraft}
      onApplyStoryDraft={applyStoryDraft}
      onApplySceneDraft={applySceneDraft}
      assistantBusy={assist.isPending}
    />
  );
}
