import React, { useState, useEffect, useCallback } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  PlayCircle,
  Loader2,
  FileText,
  Sparkles,
  History,
  AlertCircle,
  Clock,
  ImageIcon,
  Film,
} from "lucide-react";
import Button from "../Button";

const STATUS_CONFIG = {
  draft: {
    label: "Draft",
    description: "Story outline is being generated or needs approval",
    color: "bg-amber-100 text-amber-800 border-amber-200",
    icon: FileText,
  },
  approved: {
    label: "Approved",
    description: "Outline approved, ready to generate",
    color: "bg-blue-100 text-blue-800 border-blue-200",
    icon: CheckCircle2,
  },
  generating: {
    label: "Generating",
    description: "Generation in progress",
    color: "bg-purple-100 text-purple-800 border-purple-200",
    icon: Loader2,
  },
  checkpoint_review: {
    label: "Checkpoint Review",
    description: "Paused at a checkpoint for review",
    color: "bg-orange-100 text-orange-800 border-orange-200",
    icon: AlertCircle,
  },
  completed: {
    label: "Completed",
    description: "All episodes generated and assembled",
    color: "bg-emerald-100 text-emerald-800 border-emerald-200",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    description: "Generation failed",
    color: "bg-red-100 text-red-800 border-red-200",
    icon: AlertCircle,
  },
};

const WORKFLOW_LABELS = {
  creator_series: "Creator Series",
  brand_campaign: "Brand Campaign",
  social_short: "Social Short",
  educational: "Educational",
  game_lore: "Game Lore",
  narrated_image_story: "Narrated Image Story",
};

function StoryStatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  const Icon = config.icon;
  
  return (
    <Badge className={`${config.color} gap-1.5 px-3 py-1.5 text-xs font-medium`}>
      <Icon className={`h-3.5 w-3.5 ${status === "generating" ? "animate-spin" : ""}`} />
      {config.label}
    </Badge>
  );
}

function OutlineSection({ episodePlan, className }) {
  if (!episodePlan) {
    return (
      <div className={`flex flex-col items-center justify-center py-12 text-center ${className}`}>
        <FileText className="h-12 w-12 text-ash mb-4" />
        <p className="text-[15px] font-medium text-ink">No outline generated yet</p>
        <p className="text-[13px] text-steel mt-1 max-w-sm">
          The AI will generate an episode outline based on your story description.
          This may take a moment after creation.
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Synopsis */}
      {episodePlan.synopsis && (
        <div className="rounded-lg border border-fog bg-muted/30 p-4">
          <h4 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel mb-2">
            Synopsis
          </h4>
          <p className="text-[14px] text-ink leading-relaxed">
            {episodePlan.synopsis}
          </p>
        </div>
      )}

      {/* Episodes */}
      {episodePlan.episodes && episodePlan.episodes.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel">
            Episode Outline ({episodePlan.episodes.length} episodes)
          </h4>
          {episodePlan.episodes.map((episode, index) => (
            <div
              key={episode.episode_number || index}
              className="rounded-lg border border-fog p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <h5 className="text-[14px] font-medium text-ink">
                  Episode {episode.episode_number || index + 1}: {episode.title || "Untitled"}
                </h5>
                {episode.scene_count && (
                  <span className="text-[11px] text-steel">
                    {episode.scene_count} scenes
                  </span>
                )}
              </div>
              
              {episode.synopsis && (
                <p className="text-[13px] text-steel leading-relaxed">
                  {episode.synopsis}
                </p>
              )}

              {episode.themes && episode.themes.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {episode.themes.map((theme, i) => (
                    <Badge
                      key={i}
                      variant="outline"
                      className="text-[10px] px-2 py-0.5"
                    >
                      {theme}
                    </Badge>
                  ))}
                </div>
              )}

              {episode.scenes && episode.scenes.length > 0 && (
                <div className="pt-2 border-t border-mist">
                  <p className="text-[11px] font-medium text-steel mb-2">Scenes:</p>
                  <ul className="space-y-1">
                    {episode.scenes.slice(0, 5).map((scene, si) => (
                      <li key={si} className="text-[12px] text-steel flex items-start gap-2">
                        <span className="text-ash">•</span>
                        <span>{scene.title || scene.description || `Scene ${si + 1}`}</span>
                      </li>
                    ))}
                    {episode.scenes.length > 5 && (
                      <li className="text-[12px] text-steel italic">
                        +{episode.scenes.length - 5} more scenes
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* General info */}
      {(episodePlan.setting || episodePlan.themes) && (
        <div className="rounded-lg border border-fog p-4 space-y-3">
          {episodePlan.setting && (
            <div>
              <h4 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel mb-1">
                Setting
              </h4>
              <p className="text-[13px] text-ink">{episodePlan.setting}</p>
            </div>
          )}
          {episodePlan.themes && episodePlan.themes.length > 0 && (
            <div>
              <h4 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel mb-2">
                Themes
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {episodePlan.themes.map((theme, i) => (
                  <Badge
                    key={i}
                    variant="outline"
                    className="text-[11px]"
                  >
                    {theme}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HistorySection({ history, className }) {
  if (!history || history.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center py-12 text-center ${className}`}>
        <History className="h-12 w-12 text-ash mb-4" />
        <p className="text-[14px] text-steel">No history yet</p>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {history.map((entry, index) => (
        <div
          key={entry.id || index}
          className="flex gap-3 p-3 rounded-lg border border-fog"
        >
          <div className="flex-1">
            <p className="text-[13px] font-medium text-ink capitalize">
              {entry.event_type?.replace(/_/g, " ")}
            </p>
            <p className="text-[11px] text-steel mt-0.5">
              {new Date(entry.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function StoryDetailsSheet({
  open,
  onOpenChange,
  series,
  onApproveOutline,
  loading,
}) {
  const [activeTab, setActiveTab] = useState("outline");
  
  // Reset tab when sheet opens
  useEffect(() => {
    if (open) setActiveTab("outline");
  }, [open]);

  const canApproveOutline = series?.raw?.status === "draft";
  const status = series?.raw?.status || "draft";
  const episodePlan = series?.raw?.episode_plan;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <SheetTitle className="text-xl truncate">
                {series?.title || "Story Details"}
              </SheetTitle>
              <SheetDescription className="mt-1">
                View and manage your story outline and generation
              </SheetDescription>
            </div>
            <StoryStatusBadge status={status} />
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap gap-2 pt-2">
            {canApproveOutline && (
              <Button
                onClick={onApproveOutline}
                disabled={loading}
                size="sm"
                className="gap-1.5"
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                )}
                Approve Outline
              </Button>
            )}
          </div>
        </SheetHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="outline" className="gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              Outline
            </TabsTrigger>
            <TabsTrigger value="history" className="gap-1.5">
              <History className="h-3.5 w-3.5" />
              History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="outline" className="mt-4">
            <OutlineSection episodePlan={episodePlan} />
          </TabsContent>

          <TabsContent value="history" className="mt-4">
            <HistorySection history={series?.raw?.history} />
          </TabsContent>
        </Tabs>

        {/* Story Metadata Footer */}
        <div className="mt-8 pt-4 border-t border-mist">
          <h4 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel mb-3">
            Story Info
          </h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-steel">Type:</span>
              <span className="ml-2 text-ink">
                {WORKFLOW_LABELS[series?.workflow_type] || series?.workflow_type}
              </span>
            </div>
            <div>
              <span className="text-steel">Genre:</span>
              <span className="ml-2 text-ink capitalize">{series?.raw?.genre}</span>
            </div>
            <div>
              <span className="text-steel">Style:</span>
              <span className="ml-2 text-ink capitalize">{series?.raw?.style}</span>
            </div>
            <div>
              <span className="text-steel">Ratio:</span>
              <span className="ml-2 text-ink">{series?.raw?.frame_ratio}</span>
            </div>
          </div>

          {/* Reference Images Summary */}
          {(series?.raw?.workflow_state?.style_reference_urls?.length > 0 ||
            series?.raw?.workflow_state?.character_reference_urls?.length > 0 ||
            series?.raw?.workflow_state?.scene_reference_urls?.length > 0) && (
            <div className="mt-4 pt-4 border-t border-mist">
              <h4 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel mb-3">
                References
              </h4>
              <div className="flex flex-wrap gap-4 text-sm">
                {series?.raw?.workflow_state?.style_reference_urls?.length > 0 && (
                  <div className="flex items-center gap-1.5 text-steel">
                    <ImageIcon className="h-3.5 w-3.5" />
                    <span>{series.raw.workflow_state.style_reference_urls.length} style</span>
                  </div>
                )}
                {series?.raw?.workflow_state?.character_reference_urls?.length > 0 && (
                  <div className="flex items-center gap-1.5 text-steel">
                    <ImageIcon className="h-3.5 w-3.5" />
                    <span>{series.raw.workflow_state.character_reference_urls.length} character</span>
                  </div>
                )}
                {series?.raw?.workflow_state?.scene_reference_urls?.length > 0 && (
                  <div className="flex items-center gap-1.5 text-steel">
                    <Film className="h-3.5 w-3.5" />
                    <span>{series.raw.workflow_state.scene_reference_urls.length} scene</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
