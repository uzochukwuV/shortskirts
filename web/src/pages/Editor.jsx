import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Palette, Users, Plus } from "lucide-react";

import { useToast } from "@/components/ui/use-toast";
import Button from "@/components/dysentry/Button";
import Breadcrumb from "@/components/dysentry/Breadcrumb";
import SceneList from "@/components/dysentry/editor/SceneList";
import SceneStage from "@/components/dysentry/editor/SceneStage";
import AiChatPanel from "@/components/dysentry/editor/AiChatPanel";
import ExportMenu from "@/components/dysentry/editor/ExportMenu";
import SceneActionsDropdown from "@/components/dysentry/editor/SceneActionsDropdown";
import CharacterSheet from "@/components/dysentry/editor/CharacterSheet";
import EpisodeAddModal from "@/components/dysentry/editor/EpisodeAddModal";
import StyleMemoryDialog from "@/components/dysentry/editor/StyleMemoryDialog";
import {
  approveEditorScene,
  assistantForScene,
  createEditorScene,
  createEpisode,
  createCharacter,
  deleteScene,
  deleteCharacter,
  getEditorStory,
  listEditorCharacters,
  listEditorEpisodes,
  listEditorScenes,
  lockScene,
  regenerateEditorScene,
  requestEditorSceneReview,
  saveStyleMemory,
  unlockScene,
  updateCharacter,
  updateEditorScene,
} from "@/api/dysentryClient";

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
  const [adding, setAdding] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [charSheetOpen, setCharSheetOpen] = useState(false);
  const [charLoading, setCharLoading] = useState(false);
  const [episodeModalOpen, setEpisodeModalOpen] = useState(false);
  const [episodeLoading, setEpisodeLoading] = useState(false);
  const [styleOpen, setStyleOpen] = useState(false);

  const loadEpisodeScenes = useCallback(async (episodeId) => {
    const nextScenes = await listEditorScenes(seriesId, episodeId);
    setScenes(nextScenes);
    setSelectedScene(nextScenes[0] || null);
  }, [seriesId]);

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
      const nextScenes = await listEditorScenes(seriesId, firstEpisode.id);
      setScenes(nextScenes);
      setSelectedScene(nextScenes[0] || null);
    } else {
      setScenes([]);
      setSelectedScene(null);
    }
  }, [seriesId]);

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

  const selectEpisode = async (episode) => {
    setSelectedEp(episode);
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

  const patchScene = (patch) => {
    setScenes((prev) =>
      prev.map((scene) => (scene.id === selectedScene?.id ? { ...scene, ...patch } : scene)),
    );
    setSelectedScene((prev) => (prev ? { ...prev, ...patch } : prev));
  };

  const saveScene = async (nextScene) => {
    const updated = await updateEditorScene(nextScene.id, nextScene);
    patchScene(updated);
    return updated;
  };

  const handleSave = async () => {
    if (!selectedScene) return;
    try {
      await saveScene(selectedScene);
      toast({ title: "Scene saved" });
    } catch (error) {
      toast({
        title: "Could not save scene",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  const handleCheckpoint = async (status) => {
    if (!selectedScene) return;
    try {
      if (status === "approved") {
        const updated = await approveEditorScene(selectedScene.id);
        patchScene(updated);
        toast({ title: "Scene approved" });
      } else {
        const updated = await requestEditorSceneReview(selectedScene.id);
        patchScene(updated);
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

  const handleRegenerate = async () => {
    if (!selectedScene) return;
    setRegenerating(true);
    patchScene({ status: "regenerating" });
    try {
      await saveScene(selectedScene);
      await regenerateEditorScene(selectedScene.id);
      toast({ title: "Scene regeneration queued" });
    } catch (error) {
      await loadEpisodeScenes(selectedEp.id);
      toast({
        title: "Regeneration failed",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setRegenerating(false);
    }
  };

  const handleAddScene = async () => {
    if (!selectedEp) return;
    setAdding(true);
    try {
      const order = (scenes.length ? Math.max(...scenes.map((scene) => scene.order || 0)) : 0) + 1;
      const created = await createEditorScene(seriesId, selectedEp.id, {
        order,
        title: `Scene ${order}`,
        type: "video",
        script: "",
        narration: "",
      });
      setScenes((prev) => [...prev, created]);
      setSelectedScene(created);
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
      type: scenePatch.media_kind ?? selectedScene.type,
      status: "draft",
    };
    patchScene(nextScene);
    try {
      await saveScene(nextScene);
      toast({ title: "Applied to scene" });
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
        type: scenePatch.media_kind || "video",
        script: scenePatch.description || "",
        prompt: scenePatch.prompt || scenePatch.visual_prompt || scenePatch.description || "",
        visual_prompt: scenePatch.visual_prompt || scenePatch.prompt || "",
        narration: scenePatch.narration || "",
      });
      setScenes((prev) => [...prev, created]);
      setSelectedScene(created);
      toast({ title: "New scene added" });
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

  // Scene actions
  const handleDeleteScene = async (sceneId) => {
    try {
      await deleteScene(sceneId);
      setScenes((prev) => prev.filter((s) => s.id !== sceneId));
      if (selectedScene?.id === sceneId) {
        setSelectedScene(scenes.find((s) => s.id !== sceneId) || null);
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
      patchScene(updated);
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
      patchScene(updated);
      toast({ title: "Scene unlocked" });
    } catch (error) {
      toast({
        title: "Could not unlock scene",
        description: error.message,
        variant: "destructive",
      });
    }
  };

  // Character management
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
      setCharacters((prev) =>
        prev.map((c) => (c.id === characterId ? { ...c, ...updated } : c))
      );
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

  // Episode management
  const handleAddEpisode = async ({ title }) => {
    try {
      setEpisodeLoading(true);
      const nextNum = episodes.length + 1;
      const created = await createEpisode(seriesId, {
        title: title || `Episode ${nextNum}`,
        episode_number: nextNum,
      });
      setEpisodes((prev) => [...prev, created]);
      selectEpisode(created);
      setEpisodeModalOpen(false);
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

  // Export handlers
  const handleExportStart = (platforms) => {
    toast({ title: `Starting export to ${platforms.length} platform(s)...` });
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
    return <div className="flex h-screen items-center justify-center text-[14px] text-steel">Story not found.</div>;
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
          <Button variant="outline" className="px-4 py-2 text-[13px]" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
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
        {/* Episodes */}
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-steel">Episodes</span>
          <div className="flex flex-wrap items-center gap-1">
            {episodes.map((episode) => (
              <button
                key={episode.id}
                onClick={() => selectEpisode(episode)}
                className={`px-3 py-1.5 text-[14px] transition-colors ${selectedEp?.id === episode.id ? "border-b-2 border-ink font-medium text-ink" : "text-steel hover:text-ink"}`}
              >
                {String(episode.episode_number).padStart(2, "0")}
              </button>
            ))}
            <button
              onClick={() => setEpisodeModalOpen(true)}
              className="ml-1 flex h-7 w-7 items-center justify-center rounded border border-dashed border-fog text-steel hover:border-ash hover:text-ink transition-colors"
              title="Add episode"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Cast */}
        <button
          onClick={() => setCharSheetOpen(true)}
          className="flex items-center gap-2 rounded-lg border border-fog px-3 py-2 text-sm text-steel hover:border-ash hover:text-ink transition-colors"
        >
          <Users className="h-4 w-4" />
          <span>Cast</span>
          {characters.length > 0 && (
            <span className="rounded-full bg-ink px-1.5 py-0.5 text-[11px] text-white">
              {characters.length}
            </span>
        </button>
      </div>

      {/* Main Content Grid */}
      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[280px_1fr_340px]">
        <div className="min-h-0 border-r border-mist">
          <SceneList
            scenes={scenes}
            selectedId={selectedScene?.id}
            onSelect={(id) => setSelectedScene(scenes.find((scene) => scene.id === id) || null)}
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
            onRegenerate={handleRegenerate}
            onCheckpoint={handleCheckpoint}
            regenerating={regenerating}
          />
        </div>
        <div className="min-h-0">
          <AiChatPanel
            series={series}
            characters={characters}
            scene={selectedScene}
            requestAssistant={(instruction) => assistantForScene(seriesId, selectedScene?.id, instruction)}
            onApplyScenePatch={handleApplyScenePatch}
            onAddSceneFromPatch={handleAddSceneFromPatch}
          />
        </div>
      </div>

      {/* Dialogs & Sheets */}
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
