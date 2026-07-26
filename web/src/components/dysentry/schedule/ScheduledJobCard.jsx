import React from "react";
import { Film, Sparkles, Send, CalendarClock, X } from "lucide-react";

const typeMeta = {
  generate_only: { label: "Generate only", icon: Film },
  generate_and_publish: { label: "Generate and publish", icon: Send },
  publish_existing: { label: "Publish existing episode", icon: Send },
  series_continuation: { label: "Series continuation", icon: Sparkles },
};

const statusStyles = {
  pending: "text-steel border-fog",
  running: "text-signal border-signal/30",
  completed: "text-ink border-ink/20",
  failed: "text-destructive border-destructive/30",
  cancelled: "text-ash border-ash",
};

const statusLabel = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  active: "Active",
};

const platformLabel = {
  tiktok: "TikTok",
  youtube: "YouTube",
};

export default function ScheduledJobCard({ job, seriesTitle, episodeTitle, onCancel }) {
  const meta = typeMeta[job.schedule_type] || typeMeta.generate_only;
  const Icon = meta.icon;
  const dt = job.next_run_at ? new Date(job.next_run_at) : null;
  const publishPlatform = job.publish_config?.platform;
  const note = job.pipeline_config?.notes;

  return (
    <div className="rounded-lg border border-fog p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
            <Icon className="h-4 w-4 text-ink" />
          </div>
          <div>
            <p className="text-[15px] font-medium text-ink">{meta.label}</p>
            <p className="mt-0.5 text-[12px] text-steel">{seriesTitle || "—"}</p>
          </div>
        </div>
        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] ${statusStyles[job.status] || statusStyles.pending}`}>
          {statusLabel[job.status] || job.status}
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-1 text-[13px] text-steel">
        <span className="inline-flex items-center gap-1.5">
          <CalendarClock className="h-3.5 w-3.5" />
          {dt ? dt.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—"}
        </span>
        {publishPlatform && (
          <span>→ {platformLabel[publishPlatform] || publishPlatform}</span>
        )}
        {episodeTitle && <span>Ep: {episodeTitle}</span>}
      </div>

      {note && (
        <p className="mt-3 text-[13px] text-steel" style={{ lineHeight: 1.5 }}>{note}</p>
      )}

      {job.status === "pending" || job.status === "active" ? (
        <button
          onClick={() => onCancel(job)}
          className="mt-4 inline-flex items-center gap-1 text-[12px] text-steel transition-colors hover:text-destructive"
        >
          <X className="h-3.5 w-3.5" /> Cancel job
        </button>
      ) : null}
    </div>
  );
}
