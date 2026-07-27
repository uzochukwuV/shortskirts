import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, FileText, ImageIcon, Settings } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import Button from "@/components/dysentry/Button";
import ImageUpload from "@/components/dysentry/ImageUpload";
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
  const [activeTab, setActiveTab] = useState("basics");
  
  const [form, setForm] = useState({
    title: "",
    prompt: "",
    genre: "action",
    style: "anime",
    workflow_type: "creator_series",
    frame_ratio: "16:9",
    num_episodes: 1,
    num_scenes: 5,
    // Reference images
    style_reference_urls: [],
    character_reference_urls: [],
    scene_reference_urls: [],
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
        title: form.title,
        prompt: form.prompt,
        description: form.prompt,
        genre: form.genre,
        style: form.style,
        workflow_type: form.workflow_type,
        frame_ratio: form.frame_ratio,
        num_episodes: form.num_episodes,
        num_scenes: form.num_scenes,
        style_reference_urls: form.style_reference_urls,
        character_reference_urls: form.character_reference_urls,
        scene_reference_urls: form.scene_reference_urls,
      });
      onOpenChange(false);
      navigate(`/editor/${story.id}`);
    } catch (err) {
      setError(err.message || "Failed to create story");
      setLoading(false);
    }
  };

  const isBasicsValid = form.title && form.prompt;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-2xl">Create new story</DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="basics" className="gap-2">
              <FileText className="h-4 w-4" />
              <span>Basics</span>
            </TabsTrigger>
            <TabsTrigger value="references" className="gap-2">
              <ImageIcon className="h-4 w-4" />
              <span>References</span>
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2">
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </TabsTrigger>
          </TabsList>

          <form 
            id="create-story-form"
            onSubmit={handleSubmit} 
            className="flex-1 overflow-y-auto"
          >
            {error && (
              <div className="mx-6 mt-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                {error}
              </div>
            )}

            {/* BASICS TAB */}
            <TabsContent value="basics" className="px-6 py-4 space-y-6 m-0">
              {/* Title */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-ink">Title *</label>
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
                <label className="text-sm font-medium text-ink">Description *</label>
                <textarea
                  value={form.prompt}
                  onChange={(e) => handleChange("prompt", e.target.value)}
                  placeholder="A brief description of your story concept..."
                  rows={4}
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

              <div className="flex justify-end">
                <Button 
                  type="button" 
                  onClick={() => setActiveTab("references")}
                  disabled={!isBasicsValid}
                >
                  Next: References
                </Button>
              </div>
            </TabsContent>

            {/* REFERENCES TAB */}
            <TabsContent value="references" className="px-6 py-4 space-y-6 m-0">
              <div className="space-y-6">
                {/* Style References */}
                <ImageUpload
                  label="Style References"
                  hint="Up to 5 images"
                  value={form.style_reference_urls}
                  onChange={(urls) => handleChange("style_reference_urls", urls)}
                  maxImages={5}
                />
                <p className="text-xs text-steel -mt-4">
                  Visual style examples: color palettes, art styles, mood boards
                </p>

                {/* Character References */}
                <ImageUpload
                  label="Character References"
                  hint="Up to 10 images"
                  value={form.character_reference_urls}
                  onChange={(urls) => handleChange("character_reference_urls", urls)}
                  maxImages={10}
                />
                <p className="text-xs text-steel -mt-4">
                  Character designs, face references, costume inspiration
                </p>

                {/* Scene References */}
                <ImageUpload
                  label="Scene References"
                  hint="Up to 5 images"
                  value={form.scene_reference_urls}
                  onChange={(urls) => handleChange("scene_reference_urls", urls)}
                  maxImages={5}
                />
                <p className="text-xs text-steel -mt-4">
                  Location inspiration, cinematography references, lighting styles
                </p>
              </div>

              <div className="flex justify-between pt-4">
                <Button 
                  type="button" 
                  variant="outline"
                  onClick={() => setActiveTab("basics")}
                >
                  Back
                </Button>
                <Button 
                  type="button" 
                  onClick={() => setActiveTab("settings")}
                >
                  Next: Settings
                </Button>
              </div>
            </TabsContent>

            {/* SETTINGS TAB */}
            <TabsContent value="settings" className="px-6 py-4 space-y-6 m-0">
              {/* Video Ratio */}
              <div className="space-y-3">
                <label className="text-sm font-medium text-ink">Video Ratio</label>
                <div className="flex gap-3">
                  {RATIOS.map((ratio) => (
                    <button
                      key={ratio.value}
                      type="button"
                      onClick={() => handleChange("frame_ratio", ratio.value)}
                      className={`flex-1 py-3 px-4 rounded-lg border text-center transition-colors ${
                        form.frame_ratio === ratio.value
                          ? "border-primary bg-primary/5 text-ink"
                          : "border-fog hover:border-ash text-steel"
                      }`}
                    >
                      <p className="font-medium">{ratio.value}</p>
                      <p className="text-xs mt-0.5 opacity-70">
                        {ratio.label.split(" ")[0]}
                      </p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-mist bg-muted/30 p-4 space-y-3">
                <h4 className="text-sm font-medium text-ink">Summary</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-steel">Title:</span>
                  <span className="text-ink truncate">{form.title || "—"}</span>
                  <span className="text-steel">Type:</span>
                  <span className="text-ink">{WORKFLOW_TYPES.find(t => t.value === form.workflow_type)?.label}</span>
                  <span className="text-steel">Episodes:</span>
                  <span className="text-ink">{form.num_episodes}</span>
                  <span className="text-steel">Scenes/Ep:</span>
                  <span className="text-ink">{form.num_scenes}</span>
                  <span className="text-steel">Style refs:</span>
                  <span className="text-ink">{form.style_reference_urls.length} images</span>
                  <span className="text-steel">Char refs:</span>
                  <span className="text-ink">{form.character_reference_urls.length} images</span>
                  <span className="text-steel">Scene refs:</span>
                  <span className="text-ink">{form.scene_reference_urls.length} images</span>
                </div>
              </div>

              <div className="flex justify-between pt-4">
                <Button 
                  type="button" 
                  variant="outline"
                  onClick={() => setActiveTab("references")}
                >
                  Back
                </Button>
                <Button 
                  type="submit"
                  form="create-story-form"
                  disabled={loading || !isBasicsValid}
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    "Create Story"
                  )}
                </Button>
              </div>
            </TabsContent>
          </form>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
