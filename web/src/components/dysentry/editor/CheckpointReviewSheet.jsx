import React, { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  Loader2,
  PlayCircle,
  PauseCircle,
  Volume2,
  RefreshCw,
  AlertCircle,
  Clock,
  Film,
} from "lucide-react";
import Button from "../Button";

const CHECKPOINT_STATUS_CONFIG = {
  pending: {
    label: "Pending Review",
    color: "bg-amber-100 text-amber-800 border-amber-200",
  },
  approved: {
    label: "Approved",
    color: "bg-emerald-100 text-emerald-800 border-emerald-200",
  },
  running: {
    label: "Processing",
    color: "bg-blue-100 text-blue-800 border-blue-200",
  },
  failed: {
    label: "Failed",
    color: "bg-red-100 text-red-800 border-red-200",
  },
};

function CheckpointCard({
  checkpoint,
  onApprove,
  onRegenerateAudio,
  loadingCheckpointId,
  voices = [],
  selectedVoice,
  onVoiceChange,
}) {
  const [expanded, setExpanded] = useState(false);
  const statusConfig = CHECKPOINT_STATUS_CONFIG[checkpoint.status] || CHECKPOINT_STATUS_CONFIG.pending;
  const isLoading = loadingCheckpointId === checkpoint.id;
  const canApprove = checkpoint.status === "pending" && checkpoint.resume_job_id;

  return (
    <div className="rounded-lg border border-fog overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
            <Film className="h-5 w-5 text-steel" />
          </div>
          <div>
            <p className="text-[14px] font-medium text-ink">
              Checkpoint #{checkpoint.batch_number}
            </p>
            <p className="text-[12px] text-steel">
              Episodes {checkpoint.start_episode_number}–{checkpoint.end_episode_number},
              Scenes {checkpoint.start_scene_number}–{checkpoint.end_scene_number}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={statusConfig.color}>
            {statusConfig.label}
          </Badge>
          <span className="text-steel text-sm">
            {expanded ? "▲" : "▼"}
          </span>
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-mist pt-4">
          {/* Narration Audio */}
          {checkpoint.narration_text && (
            <div className="rounded-lg bg-muted/30 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Volume2 className="h-4 w-4 text-steel" />
                  <span className="text-[11px] font-medium uppercase tracking-tight-bold text-steel">
                    Narration
                  </span>
                </div>
                {checkpoint.narration_voice && (
                  <span className="text-[11px] text-steel">
                    Voice: {checkpoint.narration_voice}
                  </span>
                )}
              </div>
              <p className="text-[13px] text-ink line-clamp-3">
                {checkpoint.narration_text}
              </p>
              
              {/* Audio Preview */}
              {checkpoint.narration_audio_url && (
                <div className="mt-2">
                  <audio
                    controls
                    className="w-full h-8"
                    src={checkpoint.narration_audio_url}
                  >
                    Your browser does not support audio playback.
                  </audio>
                </div>
              )}

              {/* Audio Status */}
              {checkpoint.audio_status && checkpoint.audio_status !== "completed" && (
                <div className="flex items-center gap-2 mt-2">
                  {checkpoint.audio_status === "running" && (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />
                      <span className="text-[11px] text-blue-600">Generating audio...</span>
                    </>
                  )}
                  {checkpoint.audio_status === "pending" && (
                    <>
                      <Clock className="h-3.5 w-3.5 text-amber-600" />
                      <span className="text-[11px] text-amber-600">Audio pending...</span>
                    </>
                  )}
                </div>
              )}

              {/* Regenerate Audio */}
              {checkpoint.narration_audio_url && (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 gap-1.5"
                  onClick={() => onRegenerateAudio?.(checkpoint)}
                  disabled={isLoading || checkpoint.audio_status === "running"}
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Regenerate Audio
                </Button>
              )}
            </div>
          )}

          {/* Reviewer Notes */}
          {checkpoint.reviewer_notes && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-[11px] font-medium uppercase tracking-tight-bold text-amber-800 mb-1">
                Reviewer Notes
              </p>
              <p className="text-[13px] text-amber-900">
                {checkpoint.reviewer_notes}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <div className="text-[11px] text-steel">
              Created {new Date(checkpoint.created_at).toLocaleDateString()}
            </div>
            <div className="flex gap-2">
              {canApprove && (
                <Button
                  size="sm"
                  onClick={() => onApprove(checkpoint)}
                  disabled={isLoading}
                  className="gap-1.5"
                >
                  {isLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  )}
                  Approve & Continue
                </Button>
              )}
              {checkpoint.status === "approved" && (
                <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Approved
                </Badge>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CheckpointReviewSheet({
  open,
  onOpenChange,
  checkpoints = [],
  storyId,
  onApproveCheckpoint,
  onRegenerateAudio,
  loading,
  loadingCheckpointId,
  voices = [],
  selectedVoice,
  onVoiceChange,
}) {
  const pendingCheckpoints = checkpoints.filter((c) => c.status === "pending");
  const approvedCheckpoints = checkpoints.filter((c) => c.status === "approved");
  const otherCheckpoints = checkpoints.filter(
    (c) => c.status !== "pending" && c.status !== "approved"
  );

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <SheetTitle className="text-xl flex items-center gap-2">
                <PauseCircle className="h-5 w-5" />
                Checkpoints
              </SheetTitle>
              <SheetDescription className="mt-1">
                Review and approve generation checkpoints
              </SheetDescription>
            </div>
            {pendingCheckpoints.length > 0 && (
              <Badge className="bg-amber-100 text-amber-800 border-amber-200">
                {pendingCheckpoints.length} pending
              </Badge>
            )}
          </div>
        </SheetHeader>

        {/* Voice Selection (Global) */}
        {voices.length > 0 && (
          <div className="mt-6 p-4 rounded-lg border border-fog bg-muted/30">
            <label className="text-[11px] font-medium uppercase tracking-tight-bold text-steel block mb-2">
              Default Narration Voice
            </label>
            <select
              value={selectedVoice}
              onChange={(e) => onVoiceChange?.(e.target.value)}
              className="w-full h-9 px-3 rounded-lg border border-fog bg-white text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {voices.map((voice) => (
                <option key={voice.id} value={voice.id}>
                  {voice.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="mt-6 space-y-6">
          {/* Pending Checkpoints */}
          {pendingCheckpoints.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel">
                Pending Review ({pendingCheckpoints.length})
              </h3>
              {pendingCheckpoints.map((checkpoint) => (
                <CheckpointCard
                  key={checkpoint.id}
                  checkpoint={checkpoint}
                  onApprove={onApproveCheckpoint}
                  onRegenerateAudio={onRegenerateAudio}
                  loadingCheckpointId={loadingCheckpointId}
                  voices={voices}
                  selectedVoice={selectedVoice}
                  onVoiceChange={onVoiceChange}
                />
              ))}
            </div>
          )}

          {/* Approved Checkpoints */}
          {approvedCheckpoints.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel">
                Approved ({approvedCheckpoints.length})
              </h3>
              {approvedCheckpoints.map((checkpoint) => (
                <CheckpointCard
                  key={checkpoint.id}
                  checkpoint={checkpoint}
                  onApprove={onApproveCheckpoint}
                  onRegenerateAudio={onRegenerateAudio}
                  loadingCheckpointId={loadingCheckpointId}
                  voices={voices}
                  selectedVoice={selectedVoice}
                  onVoiceChange={onVoiceChange}
                />
              ))}
            </div>
          )}

          {/* Other Checkpoints */}
          {otherCheckpoints.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-[11px] font-medium uppercase tracking-tight-bold text-steel">
                Other ({otherCheckpoints.length})
              </h3>
              {otherCheckpoints.map((checkpoint) => (
                <CheckpointCard
                  key={checkpoint.id}
                  checkpoint={checkpoint}
                  onApprove={onApproveCheckpoint}
                  onRegenerateAudio={onRegenerateAudio}
                  loadingCheckpointId={loadingCheckpointId}
                  voices={voices}
                  selectedVoice={selectedVoice}
                  onVoiceChange={onVoiceChange}
                />
              ))}
            </div>
          )}

          {/* Empty State */}
          {checkpoints.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <PauseCircle className="h-16 w-16 text-ash mb-4" />
              <p className="text-[15px] font-medium text-ink">No checkpoints yet</p>
              <p className="text-[13px] text-steel mt-1 max-w-sm">
                Checkpoints are created during generation when the story is paused 
                for human review. Start generating to see checkpoints appear.
              </p>
            </div>
          )}
        </div>

        {/* Help Text */}
        <div className="mt-8 pt-4 border-t border-mist">
          <div className="flex items-start gap-2 text-[12px] text-steel">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <p>
              Checkpoints allow you to review generated content before continuing. 
              Approve a checkpoint to resume generation from that point.
            </p>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
