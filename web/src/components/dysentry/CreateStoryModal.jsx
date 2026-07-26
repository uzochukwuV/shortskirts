import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import Button from "@/components/dysentry/Button";
import { createStory } from "@/api/dysentryClient";

const WORKFLOW_TYPES = [
  { value: "creator_series", label: "Creator Series", desc: "Serialized anime/fiction series" },
  { value: "brand_campaign", label: "Brand Campaign", desc: "Ad concepts from product brief" },
  { value: "social_short", label: "Social Short", desc: "TikTok/Reels/Shorts vertical" },
  { value: "educational", label: "Educational", desc: "Animated explainer or course" },
  { value: "game_lore", label: "Game Lore", desc: "IP lore trailers or teasers" },
  { value: "narrated_image_story", label: "Narrated Image Story", desc: "Still-image story with narration" },
];

const GENRES = [
  "action", "comedy", "drama", "horror", "romance", 
  "sci-fi", "fantasy", "thriller", "documentary", "other"
];

const STYLES = [
  "anime", "cartoon", "3d", "realistic", "sketch", 
  "pixel", "comic", "cinematic", "minimalist"
];

const RATIOS = [
  { value: "16:9", label: "16:9 (Landscape)" },
  { value: "9:16", label: "9:16 (Vertical)" },
  { value: "1:1", label: "1:1 (Square)" },
];

export default function CreateStoryModal({ open, onOpenChange }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [form, setForm] = useState({
    title: "",
    prompt: "",
    genre: "action",
    style: "anime",
    workflow_type: "creator_series",
    frame_ratio: "16:9",
    num_episodes: 1,
    num_scenes: 5,
  });

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const story = await createStory({
        ...form,
        description: form.prompt,
      });
      onOpenChange(false);
      navigate(`/editor/${story.id}`);
    } catch (err) {
      setError(err.message || "Failed to create story");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl">Create new story</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
              {error}
            </div>
          )}

          {/* Title */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-ink">Title</label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => handleChange("title", e.target.value)}
              placeholder="My Awesome Story"
              className="w-full h-11 px-4 rounded-lg border border-fog bg-paper text-ink placeholder:text-steel focus:outline-none focus:ring-2 focus:ring-primary/50"
              required
            />
          </div>

          {/* Prompt / Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-ink">Description</label>
            <textarea
              value={form.prompt}
              onChange={(e) => handleChange("prompt", e.target.value)}
              placeholder="A brief description of your story concept..."
              rows={3}
              className="w-full px-4 py-3 rounded-lg border border-fog bg-paper text-ink placeholder:text-steel focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
              required
            />
          </div>

          {/* Workflow Type */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-ink">Story Type</label>
            <div className="grid grid-cols-2 gap-3">
              {WORKFLOW_TYPES.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => handleChange("workflow_type", type.value)}
                  className={`p-3 rounded-lg border text-left transition-colors ${
                    form.workflow_type === type.value
                      ? "border-primary bg-primary/5"
                      : "border-fog hover:border-ash"
                  }`}
                >
                  <p className="font-medium text-ink">{type.label}</p>
                  <p className="text-xs text-steel mt-0.5">{type.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Genre & Style */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-ink">Genre</label>
              <select
                value={form.genre}
                onChange={(e) => handleChange("genre", e.target.value)}
                className="w-full h-11 px-4 rounded-lg border border-fog bg-paper text-ink focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {GENRES.map((genre) => (
                  <option key={genre} value={genre}>
                    {genre.charAt(0).toUpperCase() + genre.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-ink">Visual Style</label>
              <select
                value={form.style}
                onChange={(e) => handleChange("style", e.target.value)}
                className="w-full h-11 px-4 rounded-lg border border-fog bg-paper text-ink focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                {STYLES.map((style) => (
                  <option key={style} value={style}>
                    {style.charAt(0).toUpperCase() + style.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Video Ratio */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-ink">Video Ratio</label>
            <div className="flex gap-3">
              {RATIOS.map((ratio) => (
                <button
                  key={ratio.value}
                  type="button"
                  onClick={() => handleChange("frame_ratio", ratio.value)}
                  className={`flex-1 py-2 px-4 rounded-lg border text-center transition-colors ${
                    form.frame_ratio === ratio.value
                      ? "border-primary bg-primary/5 text-ink"
                      : "border-fog hover:border-ash text-steel"
                  }`}
                >
                  {ratio.label}
                </button>
              ))}
            </div>
          </div>

          {/* Episodes & Scenes */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-ink">Episodes</label>
              <input
                type="number"
                min={1}
                max={5}
                value={form.num_episodes}
                onChange={(e) => handleChange("num_episodes", parseInt(e.target.value) || 1)}
                className="w-full h-11 px-4 rounded-lg border border-fog bg-paper text-ink focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <p className="text-xs text-steel">1-5 episodes</p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-ink">Scenes per Episode</label>
              <input
                type="number"
                min={3}
                max={10}
                value={form.num_scenes}
                onChange={(e) => handleChange("num_scenes", parseInt(e.target.value) || 5)}
                className="w-full h-11 px-4 rounded-lg border border-fog bg-paper text-ink focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <p className="text-xs text-steel">3-10 scenes</p>
            </div>
          </div>

          <DialogFooter className="pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !form.title || !form.prompt}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Story"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
