import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Palette, Users, Plus, CheckCircle2, Clapperboard, Loader2 } from "lucide-react";

import { useToast } from "@/components/ui/use-toast";
import Button from "@/components/dysentry/Button";
import Breadcrumb from "@/components/dysentry/Breadcrumb";
import SceneList from "@/components/dysentry/editor/SceneList";
import SceneStage from "@/components/dysentry/editor/SceneStage";
import AiChatPanel from "@/components/dysentry/editor/AiChatPanel";
import ExportMenu from "@/components/dysentry/editor/ExportMenu";
import CharacterSheet from "@/components/dysentry/editor/CharacterSheet";
import EpisodeAddModal from "@/components/dysentry/editor/EpisodeAddModal";
import StyleMemoryDialog from "@/components/dysentry/editor/StyleMemoryDialog";
import {
  approveEditorScene,
  assembleEpisode,
  assistantForScene,
  bulkApproveEpisode,
  createEditorScene,
  createEpisode,
  createCharacter,
  deleteScene,
  deleteCharacter,
  getEditorScene,
  getEditorStory,
  listEditorCharacters,
  listEditorEpisodes,
  listEditorScenes,
  lockScene,
  pollSceneJob,
  regenerateEditorScene,
  rejectScene,
  requestEditorSceneReview,
  saveStyleMemory,
  unlockScene,
  updateCharacter,
  updateEditorScene,
} from "@/api/dysentryClient";

function sceneContentKey(scene) {
  if (!scene) return "";
  return JSON.stringify({
    title: scene.title || "",
    script: scene.script || "",
    prompt: scene.prompt || "",
    visual_prompt: scene.visual_prompt || "",
    narration: scene.narration || "",
    mood: scene.mood || "",
    location: scene.location || "",
    type: scene.type || "",
    checkpoint_notes: scene.checkpoint_notes || "",
  });
}

export default function Editor() {
  const { seriesId } = useParams();
  const { toast } = useToast();
  const [series, setSeries] = useState(null);
  const [episodes, setEpisodes] = useState([]);
  const [selectedEp, setSelectedEp] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [selectedScene, setSelectedScene] = useState(null);
  const [characters, setCharacters] = useState([]);
  const [regenerating, setRegenerating] = useState(false);
  const [jobStep, setJobStep] = useState("");
  const [adding, setAdding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [charSheetOpen, setCharSheetOpen] = useState(false);
  const [charLoading, setCharLoading] = useState(false);
  const [episodeModalOpen, setEpisodeModalOpen] = useState(false);
  const [episodeLoading, setEpisodeLoading] = useState(false);
  const [styleOpen, setStyleOpen] = useState(false);
  const [savedContentKey, setSavedContentKey] = useState("");
  const [bulkApproving, setBulkApproving] = useState(false);
  const [assembling, setAssembling] = useState(false);
  const pollCancelRef = useRef(0);
  const saveHandlerRef = useRef(null);

  const dirty = useMemo(() => {
    if (!selectedScene) return false;
    return sceneContentKey(selectedScene) !== savedContentKey;
  }, [selectedScene, savedContentKey]);

  const episodeStats = useMemo(() => {
    const total = scenes.length;
    const approved = scenes.filter(
      (s) => s.status === "approved" || s.approval_status === "approved",
    ).length;
    const ready = scenes.filter((s) => s.status === "ready" || s.status === "pending_review").length;
    const generating = scenes.filter((s) => s.status === "regenerating").length;
    return { total, approved, ready, generating };
  }, [scenes]);

  const markSaved = useCallback((scene) => {
    setSavedContentKey(sceneContentKey(scene));
  }, []);

  const loadEpisodeScenes = useCallback(
    async (episodeId, { preferSceneId } = {}) => {
      const nextScenes = await listEditorScenes(seriesId, episodeId);
      setScenes(nextScenes);
      setSelectedScene((prev) => {
        const keepId = preferSceneId || prev?.id;
        const kept = keepId ? nextScenes.find((s) => s.id === keepId) : null;
        const next = kept || nextScenes[0] || null;
        if (next) setSavedContentKey(sceneContentKey(next));
        else setSavedContentKey("");
        return next;
      });
      return nextScenes;
    },
    [seriesId],
  );

  const loadAll = useCallback(async () => {
    const [story, eps, chars] = await Promise.all([
      getEditorStory(seriesId),
      listEditorEpisodes(seriesId),
      listEditorCharacters(seriesId),
    ]);
    setSeries(story);
    setEpisodes(eps);
    setCharacters(chars);
    const firstEpisode = eps[0] || null;
    setSelectedEp(firstEpisode);
    if (firstEpisode) {
      await loadEpisodeScenes(firstEpisode.id);
    } else {
      setScenes([]);
      setSelectedScene(null);
      setSavedContentKey("");
    }
  }, [seriesId, loadEpisodeScenes]);

  useEffect(() => {
    (async () => {
      try {
        await loadAll();
      } catch (error) {
        toast({
          title: "Could not load editor",
          description: error.message,
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    })();
  }, [loadAll, toast]);

  // Warn before leaving with unsaved edits
  useEffect(() => {
    const onBeforeUnload = (e) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  // Ctrl/Cmd+S to save
  useEffect(() => {
    const onKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        saveHandlerRef.current?.();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const selectEpisode = async (episode) => {
    if (dirty) {
      const ok = window.confirm("You have unsaved changes. Switch episode anyway?");
      if (!ok) return;
    }
    setSelectedEp(episode);
    setJobStep("");
    try {
      await loadEpisodeScenes(episode.id);
    } catch (error) {
      toast({
        title: "Could not load episode scenes",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const selectScene = (id) => {
    if (selectedScene?.id === id) return;
    if (dirty) {
      const ok = window.confirm("You have unsaved changes. Switch scene anyway?");
      if (!ok) return;
    }
    const next = scenes.find((scene) => scene.id === id) || null;
    setSelectedScene(next);
    setSavedContentKey(sceneContentKey(next));
    setJobStep("");
  };

  const patchScene = (patch, sceneId = selectedScene?.id) => {
    if (!sceneId) return;
    setScenes((prev) =>
      prev.map((scene) => (scene.id === sceneId ? { ...scene, ...patch } : scene)),
    );
    setSelectedScene((prev) => (prev && prev.id === sceneId ? { ...prev, ...patch } : prev));
  };

  const replaceScene = (updated) => {
    setScenes((prev) => prev.map((scene) => (scene.id === updated.id ? updated : scene)));
    setSelectedScene((prev) => (prev && prev.id === updated.id ? updated : prev));
    if (!selectedScene || selectedScene.id === updated.id) {
      markSaved(updated);
    }
  };

  const saveScene = async (nextScene) => {
    const updated = await updateEditorScene(nextScene.id, nextScene);
    replaceScene(updated);
    return updated;
  };

  const handleSave = async () => {
    if (!selectedScene || saving || !dirty) return;
    setSaving(true);
    try {
      await saveScene(selectedScene);
      toast({ title: "Scene saved" });
    } catch (error) {
      toast({
        title: "Could not save scene",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };
  saveHandlerRef.current = handleSave;

  const handleCheckpoint = async (status) => {
    if (!selectedScene) return;
    try {
      if (dirty) {
        await saveScene(selectedScene);
      }
      if (status === "approved") {
        const updated = await approveEditorScene(selectedScene.id);
        replaceScene(updated);
        toast({ title: "Scene approved" });
      } else {
        const updated = await requestEditorSceneReview(selectedScene.id);
        replaceScene(updated);
        toast({ title: "Scene sent for review" });
      }
    } catch (error) {
      toast({
        title: "Update failed",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleReject = async () => {
    if (!selectedScene) return;
    try {
      if (dirty) {
        await saveScene(selectedScene);
      }
      const updated = await rejectScene(selectedScene.id);
      replaceScene(updated);
      toast({
        title: "Scene rejected",
        description: "Approval cleared — edit and regenerate when ready.",
      });
    } catch (error) {
      toast({
        title: "Could not reject scene",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleRegenerate = async () => {
    if (!selectedScene) return;
    if (selectedScene.locked) {
      toast({
        title: "Scene is locked",
        description: "Unlock it before regenerating.",
        variant: "destructive",
      });
      return;
    }

    const sceneId = selectedScene.id;
    const token = ++pollCancelRef.current;
    setRegenerating(true);
    setJobStep("Saving scene…");
    patchScene({ status: "regenerating", approval_status: "pending" }, sceneId);

    try {
      // Always persist current form so regen uses latest prompts.
      await saveScene(selectedScene);
      setJobStep("Queuing generation…");
      const job = await regenerateEditorScene(sceneId);
      toast({ title: "Media generation started" });

      if (job?.id) {
        setJobStep(job.current_step || "Running…");
        const finalJob = await pollSceneJob(job.id, {
          intervalMs: 2000,
          timeoutMs: 5 * 60 * 1000,
          onTick: (tick) => {
            if (pollCancelRef.current !== token) return;
            setJobStep(tick.current_step || tick.status || "Running…");
          },
        });

        if (pollCancelRef.current !== token) return;

        if ((finalJob.status || "").toLowerCase() === "failed") {
          throw new Error(finalJob.error || "Generation failed");
        }

        // Prefer single-scene refresh to keep selection stable.
        try {
          const fresh = await getEditorScene(sceneId);
          replaceScene(fresh);
        } catch {
          await loadEpisodeScenes(selectedEp.id, { preferSceneId: sceneId });
        }
        setJobStep("");
        toast({ title: "Media ready for review" });
      } else {
        // Backend didn't return a job id — fall back to a delayed refetch.
        await new Promise((r) => setTimeout(r, 3000));
        await loadEpisodeScenes(selectedEp.id, { preferSceneId: sceneId });
        toast({ title: "Regeneration queued" });
      }
    } catch (error) {
      if (pollCancelRef.current === token) {
        try {
          const fresh = await getEditorScene(sceneId);
          replaceScene(fresh);
        } catch {
          if (selectedEp) await loadEpisodeScenes(selectedEp.id, { preferSceneId: sceneId });
        }
        toast({
          title: "Generation failed",
          description: error.message,
          variant: "destructive",
        });
      }
    } finally {
      if (pollCancelRef.current === token) {
        setRegenerating(false);
        setJobStep("");
      }
    }
  };

  const handleAddScene = async () => {
    if (!selectedEp) return;
    if (dirty) {
      const ok = window.confirm("You have unsaved changes. Add a scene anyway?");
      if (!ok) return;
    }
    setAdding(true);
    try {
      const order = (scenes.length ? Math.max(...scenes.map((scene) => scene.order || 0)) : 0) + 1;
      const created = await createEditorScene(seriesId, selectedEp.id, {
        order,
        title: `Scene ${order}`,
        type: "video",
        script: "",
        visual_prompt: "",
        narration: "",
      });
      setScenes((prev) => [...prev, created]);
      setSelectedScene(created);
      markSaved(created);
      toast({ title: "Scene added" });
    } catch (error) {
      toast({
        title: "Could not add scene",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setAdding(false);
    }
  };

  const handleApplyScenePatch = async (scenePatch) => {
    if (!selectedScene || !scenePatch) return;
    const nextScene = {
      ...selectedScene,
      title: scenePatch.title ?? selectedScene.title,
      script: scenePatch.description ?? selectedScene.script,
      prompt: scenePatch.prompt ?? scenePatch.visual_prompt ?? selectedScene.prompt,
      visual_prompt: scenePatch.visual_prompt ?? selectedScene.visual_prompt,
      narration: scenePatch.narration ?? selectedScene.narration,
      mood: scenePatch.mood ?? selectedScene.mood,
      location: scenePatch.location ?? selectedScene.location,
      type: scenePatch.media_kind
        ? scenePatch.media_kind === "image"
          ? "narrated_image"
          : scenePatch.media_kind === "voice"
            ? "voice"
            : "video"
        : selectedScene.type,
      // Text edits after media should drop back to draft-ish UX until re-approved.
      status:
        selectedScene.status === "approved" || selectedScene.status === "ready"
          ? "draft"
          : selectedScene.status,
    };
    patchScene(nextScene);
    try {
      const saved = await saveScene(nextScene);
      toast({ title: "Applied AI patch to scene" });
      return saved;
    } catch (error) {
      toast({
        title: "Could not save scene",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleAddSceneFromPatch = async (scenePatch) => {
    if (!selectedEp || !scenePatch) return;
    try {
      const order = (scenes.length ? Math.max(...scenes.map((scene) => scene.order || 0)) : 0) + 1;
      const created = await createEditorScene(seriesId, selectedEp.id, {
        order,
        title: scenePatch.title || `Scene ${order}`,
        type:
          scenePatch.media_kind === "image"
            ? "narrated_image"
            : scenePatch.media_kind === "voice"
              ? "voice"
              : "video",
        script: scenePatch.description || "",
        prompt: scenePatch.prompt || scenePatch.visual_prompt || scenePatch.description || "",
        visual_prompt: scenePatch.visual_prompt || scenePatch.prompt || "",
        narration: scenePatch.narration || "",
        mood: scenePatch.mood || "",
        location: scenePatch.location || "",
      });
      setScenes((prev) => [...prev, created]);
      setSelectedScene(created);
      markSaved(created);
      toast({ title: "New scene added from AI draft" });
    } catch (error) {
      toast({
        title: "Could not add scene",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleStyleSave = async (value) => {
    try {
      const updated = await saveStyleMemory(seriesId, series, value);
      setSeries(updated);
      toast({ title: "Style memory saved" });
    } catch (error) {
      toast({
        title: "Could not save style memory",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleDeleteScene = async (sceneId) => {
    const target = scenes.find((s) => s.id === sceneId);
    const ok = window.confirm(`Delete “${target?.title || "this scene"}”? This cannot be undone.`);
    if (!ok) return;
    try {
      await deleteScene(sceneId);
      const remaining = scenes.filter((s) => s.id !== sceneId);
      setScenes(remaining);
      if (selectedScene?.id === sceneId) {
        const next = remaining[0] || null;
        setSelectedScene(next);
        markSaved(next);
      }
      toast({ title: "Scene deleted" });
    } catch (error) {
      toast({
        title: "Could not delete scene",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleLockScene = async (sceneId) => {
    try {
      const updated = await lockScene(sceneId);
      replaceScene(updated);
      toast({ title: "Scene locked" });
    } catch (error) {
      toast({
        title: "Could not lock scene",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleUnlockScene = async (sceneId) => {
    try {
      const updated = await unlockScene(sceneId);
      replaceScene(updated);
      toast({ title: "Scene unlocked" });
    } catch (error) {
      toast({
        title: "Could not unlock scene",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleAddCharacter = async (character) => {
    try {
      setCharLoading(true);
      const created = await createCharacter(seriesId, character);
      setCharacters((prev) => [...prev, created]);
      toast({ title: "Character added" });
    } catch (error) {
      toast({
        title: "Could not add character",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setCharLoading(false);
    }
  };

  const handleUpdateCharacter = async (characterId, character) => {
    try {
      setCharLoading(true);
      const updated = await updateCharacter(characterId, character);
      setCharacters((prev) => prev.map((c) => (c.id === characterId ? { ...c, ...updated } : c)));
      toast({ title: "Character updated" });
    } catch (error) {
      toast({
        title: "Could not update character",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setCharLoading(false);
    }
  };

  const handleDeleteCharacter = async (characterId) => {
    try {
      setCharLoading(true);
      await deleteCharacter(characterId);
      setCharacters((prev) => prev.filter((c) => c.id !== characterId));
      toast({ title: "Character deleted" });
    } catch (error) {
      toast({
        title: "Could not delete character",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setCharLoading(false);
    }
  };

  const handleAddEpisode = async ({ title }) => {
    try {
      setEpisodeLoading(true);
      const nextNum = episodes.length + 1;
      const created = await createEpisode(seriesId, {
        title: title || `Episode ${nextNum}`,
        episode_number: nextNum,
      });
      setEpisodes((prev) => [...prev, created]);
      setEpisodeModalOpen(false);
      await selectEpisode(created);
      toast({ title: "Episode added" });
    } catch (error) {
      toast({
        title: "Could not add episode",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setEpisodeLoading(false);
    }
  };

  const handleBulkApprove = async () => {
    if (!selectedEp) return;
    const pending = scenes.filter(
      (s) => s.approval_status !== "approved" && !s.locked,
    ).length;
    if (pending === 0) {
      toast({ title: "Nothing to approve", description: "All unlockable scenes are already approved." });
      return;
    }
    const ok = window.confirm(
      `Approve ${pending} scene${pending === 1 ? "" : "s"} in this episode? Locked scenes are skipped.`,
    );
    if (!ok) return;
    setBulkApproving(true);
    try {
      const result = await bulkApproveEpisode(selectedEp.id);
      await loadEpisodeScenes(selectedEp.id, { preferSceneId: selectedScene?.id });
      toast({
        title: `Approved ${result.approved_scene_ids?.length || 0} scene(s)`,
        description: result.all_approved
          ? "Episode is fully approved — you can assemble."
          : `${result.skipped_scene_ids?.length || 0} scene(s) skipped.`,
      });
    } catch (error) {
      toast({
        title: "Bulk approve failed",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setBulkApproving(false);
    }
  };

  const handleAssemble = async () => {
    if (!selectedEp) return;
    setAssembling(true);
    try {
      const result = await assembleEpisode(selectedEp.id);
      toast({
        title: "Assembly queued",
        description: result.message || `Job ${result.job_id}`,
      });
      // Refresh episode list so assembled_video_url can appear later
      const eps = await listEditorEpisodes(seriesId);
      setEpisodes(eps);
      const refreshed = eps.find((e) => e.id === selectedEp.id);
      if (refreshed) setSelectedEp(refreshed);
    } catch (error) {
      // Backend 409 returns structured detail about unapproved scenes
      const detail = error?.detail || error?.message || "Assembly failed";
      const message =
        typeof detail === "object" ? detail.message || JSON.stringify(detail) : String(detail);
      toast({
        title: "Cannot assemble yet",
        description: message,
        variant: "destructive",
      });
    } finally {
      setAssembling(false);
    }
  };

  const handleExportStart = (platforms) => {
    toast({ title: `Starting export to ${platforms.length} platform(s)…` });
  };

  const handleExportComplete = (results) => {
    const successful = results.filter((r) => r.success);
    if (successful.length > 0) {
      toast({ title: `Exported to ${successful.length} platform(s)` });
    }
    const failed = results.filter((r) => !r.success);
    failed.forEach((f) => {
      toast({
        title: `Export failed: ${f.platform}`,
        description: f.error,
        variant: "destructive",
      });
    });
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-mist border-t-ink" />
      </div>
    );
  }
  if (!series) {
    return (
      <div className="flex h-screen items-center justify-center text-[14px] text-steel">
        Story not found.
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-paper">
      {/* Header */}
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-mist px-6 py-3">
        <Link to="/" className="font-display text-[18px] font-medium tracking-tight-bold text-ink">
          Dysentry
        </Link>
        <span className="text-ash">/</span>
        <Breadcrumb items={[{ label: "Studio", path: "/dashboard" }, { label: series.title }]} />
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" className="px-4 py-2 text-[13px]" onClick={() => setStyleOpen(true)}>
            <Palette className="h-4 w-4" /> Style
          </Button>
          <Button
            variant="outline"
            className="px-4 py-2 text-[13px]"
            onClick={handleSave}
            disabled={saving || !dirty || !selectedScene}
          >
            {saving ? "Saving…" : dirty ? "Save" : "Saved"}
          </Button>
          <ExportMenu
            episode={selectedEp}
            onExportStart={handleExportStart}
            onExportComplete={handleExportComplete}
          />
        </div>
      </header>

      {/* Episode & Character Bar */}
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b border-mist px-6 py-3">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-steel">Episodes</span>
            <div className="flex flex-wrap items-center gap-1">
              {episodes.map((episode) => (
                <button
                  key={episode.id}
                  onClick={() => selectEpisode(episode)}
                  className={`px-3 py-1.5 text-[14px] transition-colors ${
                    selectedEp?.id === episode.id
                      ? "border-b-2 border-ink font-medium text-ink"
                      : "text-steel hover:text-ink"
                  }`}
                  title={episode.title}
                >
                  {String(episode.episode_number).padStart(2, "0")}
                </button>
              ))}
              <button
                onClick={() => setEpisodeModalOpen(true)}
                className="ml-1 flex h-7 w-7 items-center justify-center rounded border border-dashed border-fog text-steel transition-colors hover:border-ash hover:text-ink"
                title="Add episode"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>

          {selectedEp && episodeStats.total > 0 && (
            <div className="hidden items-center gap-2 text-[12px] text-steel sm:flex">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              <span>
                {episodeStats.approved}/{episodeStats.total} approved
              </span>
              {episodeStats.ready > 0 && (
                <span className="text-sky-700">· {episodeStats.ready} ready for review</span>
              )}
              {episodeStats.generating > 0 && (
                <span className="text-signal">· {episodeStats.generating} generating</span>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {selectedEp && episodeStats.total > 0 && (
            <>
              <Button
                variant="outline"
                className="px-3 py-2 text-[12px]"
                onClick={handleBulkApprove}
                disabled={bulkApproving || episodeStats.approved === episodeStats.total}
              >
                {bulkApproving ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                )}
                Approve all
              </Button>
              <Button
                variant={episodeStats.approved === episodeStats.total ? "primary" : "outline"}
                className="px-3 py-2 text-[12px]"
                onClick={handleAssemble}
                disabled={assembling || episodeStats.total === 0}
                title={
                  episodeStats.approved === episodeStats.total
                    ? "Assemble approved scenes into an episode video"
                    : "All scenes must be approved first"
                }
              >
                {assembling ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Clapperboard className="h-3.5 w-3.5" />
                )}
                Assemble
              </Button>
            </>
          )}
          <button
            onClick={() => setCharSheetOpen(true)}
            className="flex items-center gap-2 rounded-lg border border-fog px-3 py-2 text-sm text-steel transition-colors hover:border-ash hover:text-ink"
          >
            <Users className="h-4 w-4" />
            <span>Cast</span>
            {characters.length > 0 && (
              <span className="rounded-full bg-ink px-1.5 py-0.5 text-[11px] text-white">
                {characters.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[280px_1fr_340px]">
        <div className="min-h-0 border-r border-mist">
          <SceneList
            scenes={scenes}
            selectedId={selectedScene?.id}
            onSelect={selectScene}
            onAdd={handleAddScene}
            adding={adding}
            onDelete={handleDeleteScene}
            onLock={handleLockScene}
            onUnlock={handleUnlockScene}
          />
        </div>
        <div className="min-h-0 overflow-hidden border-r border-mist">
          <SceneStage
            scene={selectedScene}
            onChange={patchScene}
            onSave={handleSave}
            onRegenerate={handleRegenerate}
            onCheckpoint={handleCheckpoint}
            onReject={handleReject}
            regenerating={regenerating}
            saving={saving}
            dirty={dirty}
            jobStep={jobStep}
          />
        </div>
        <div className="min-h-0">
          <AiChatPanel
            series={series}
            characters={characters}
            scene={selectedScene}
            requestAssistant={(instruction) =>
              assistantForScene(seriesId, selectedScene?.id, instruction)
            }
            onApplyScenePatch={handleApplyScenePatch}
            onAddSceneFromPatch={handleAddSceneFromPatch}
          />
        </div>
      </div>

      <CharacterSheet
        open={charSheetOpen}
        onOpenChange={setCharSheetOpen}
        characters={characters}
        onAddCharacter={handleAddCharacter}
        onUpdateCharacter={handleUpdateCharacter}
        onDeleteCharacter={handleDeleteCharacter}
        loading={charLoading}
      />

      <EpisodeAddModal
        open={episodeModalOpen}
        onOpenChange={setEpisodeModalOpen}
        onAdd={handleAddEpisode}
        loading={episodeLoading}
      />

      <StyleMemoryDialog
        open={styleOpen}
        onOpenChange={setStyleOpen}
        value={series?.style_memory}
        onSave={handleStyleSave}
      />
    </div>
  );
}
