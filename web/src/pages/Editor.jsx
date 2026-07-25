import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Palette } from "lucide-react";

import { useToast } from "@/components/ui/use-toast";
import Button from "@/components/dysentry/Button";
import Breadcrumb from "@/components/dysentry/Breadcrumb";
import SceneList from "@/components/dysentry/editor/SceneList";
import SceneStage from "@/components/dysentry/editor/SceneStage";
import AiChatPanel from "@/components/dysentry/editor/AiChatPanel";
import ExportMenu from "@/components/dysentry/editor/ExportMenu";
import CharacterDialog from "@/components/dysentry/editor/CharacterDialog";
import StyleMemoryDialog from "@/components/dysentry/editor/StyleMemoryDialog";
import {
  approveEditorScene,
  assistantForScene,
  createEditorScene,
  getEditorStory,
  listEditorCharacters,
  listEditorEpisodes,
  listEditorScenes,
  regenerateEditorScene,
  requestEditorSceneReview,
  saveStyleMemory,
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
  const [activeChar, setActiveChar] = useState(null);
  const [charOpen, setCharOpen] = useState(false);
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

  const handleExport = (platforms) => {
    toast({ title: `Export prepared for ${platforms.join(", ")}` });
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
          <Button variant="outline" className="px-4 py-2 text-[13px]" onClick={handleSave}>
            Save
          </Button>
          <ExportMenu onExport={handleExport} />
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-mist px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-steel">Episode</span>
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
            {episodes.length === 0 && <span className="text-[13px] text-steel">No episodes</span>}
          </div>
        </div>
        {characters.length > 0 && (
          <div className="ml-auto flex items-center gap-2">
            <span className="text-[11px] text-steel">Cast</span>
            <div className="flex flex-wrap items-center gap-1.5">
              {characters.map((character) => (
                <button
                  key={character.id}
                  onClick={() => {
                    setActiveChar(character);
                    setCharOpen(true);
                  }}
                  title={character.name}
                  className="flex items-center gap-1.5 rounded-full border border-fog py-1 pl-1 pr-3 transition-colors hover:border-ash"
                >
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-ink text-[11px] font-medium text-white">
                    {character.name?.[0]}
                  </div>
                  <span className="text-[12px] text-ink">{character.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[280px_1fr_340px]">
        <div className="min-h-0 border-r border-mist">
          <SceneList
            scenes={scenes}
            selectedId={selectedScene?.id}
            onSelect={(id) => setSelectedScene(scenes.find((scene) => scene.id === id) || null)}
            onAdd={handleAddScene}
            adding={adding}
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

      <CharacterDialog character={activeChar} open={charOpen} onOpenChange={setCharOpen} />
      <StyleMemoryDialog
        open={styleOpen}
        onOpenChange={setStyleOpen}
        value={series?.style_memory}
        onSave={handleStyleSave}
      />
    </div>
  );
}
