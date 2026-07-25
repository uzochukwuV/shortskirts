import React, { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";

import { useToast } from "@/components/ui/use-toast";
import Button from "../Button";
import { createSchedule, listEditorEpisodes } from "@/api/dysentryClient";

const jobTypes = [
  { id: "generate_only", label: "Generate only" },
  { id: "generate_and_publish", label: "Generate and publish" },
  { id: "publish_existing", label: "Publish existing episode" },
  { id: "series_continuation", label: "Series continuation" },
];

const platforms = [
  { id: "tiktok", label: "TikTok" },
  { id: "youtube", label: "YouTube" },
];

export default function ScheduleForm({ open, onOpenChange, series, onCreated }) {
  const { toast } = useToast();
  const [jobType, setJobType] = useState("generate_only");
  const [seriesId, setSeriesId] = useState("");
  const [episodes, setEpisodes] = useState([]);
  const [episodeId, setEpisodeId] = useState("");
  const [platform, setPlatform] = useState("youtube");
  const [time, setTime] = useState("");
  const [notes, setNotes] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (open && series.length && !seriesId) setSeriesId(series[0].id);
  }, [open, series, seriesId]);

  useEffect(() => {
    if (!seriesId) {
      setEpisodes([]);
      setEpisodeId("");
      return;
    }
    (async () => {
      try {
        const eps = await listEditorEpisodes(seriesId);
        setEpisodes(eps);
        setEpisodeId("");
      } catch {
        setEpisodes([]);
      }
    })();
  }, [seriesId]);

  const reset = () => {
    setJobType("generate_only");
    setSeriesId(series[0]?.id || "");
    setEpisodeId("");
    setPlatform("youtube");
    setTime("");
    setNotes("");
  };

  const submit = async () => {
    if (!seriesId) {
      toast({ title: "Select a series", variant: "destructive" });
      return;
    }
    if (!time) {
      toast({ title: "Pick a date and time", variant: "destructive" });
      return;
    }
    if (jobType === "publish_existing" && !episodeId) {
      toast({ title: "Select an episode to publish", variant: "destructive" });
      return;
    }
    setCreating(true);
    try {
      await createSchedule({
        name: notes || `${jobTypes.find((type) => type.id === jobType)?.label || "Automation"} — ${new Date(time).toLocaleString()}`,
        schedule_type: jobType,
        story_id: seriesId,
        cadence: "once",
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        next_run_at: new Date(time).toISOString(),
        pipeline_config: notes ? { notes } : {},
        publish_config:
          jobType === "publish_existing" || jobType === "generate_and_publish"
            ? { platform, episode_id: episodeId || null }
            : {},
        approval_policy: jobType === "generate_and_publish" ? "auto_publish" : "require_approval",
      });
      toast({ title: "Job scheduled" });
      onCreated();
      onOpenChange(false);
      reset();
    } catch (error) {
      toast({ title: "Could not schedule job", description: error.message, variant: "destructive" });
    } finally {
      setCreating(false);
    }
  };

  const isPublish = jobType === "publish_existing" || jobType === "generate_and_publish";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="font-display text-[16px] font-medium tracking-tight-bold text-ink">
            Schedule a job
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <Field label="What to schedule">
            <Select value={jobType} onValueChange={setJobType}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {jobTypes.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field label="Series">
            <Select value={seriesId} onValueChange={setSeriesId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select series" />
              </SelectTrigger>
              <SelectContent>
                {series.length === 0 && (
                  <SelectItem value="_none" disabled>
                    No series
                  </SelectItem>
                )}
                {series.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          {isPublish && (
            <Field label="Episode to publish">
              <Select value={episodeId} onValueChange={setEpisodeId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select episode" />
                </SelectTrigger>
                <SelectContent>
                  {episodes.length === 0 && (
                    <SelectItem value="_none" disabled>
                      No episodes
                    </SelectItem>
                  )}
                  {episodes.map((e) => (
                    <SelectItem key={e.id} value={e.id}>
                      Ep {e.episode_number}: {e.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          )}

          {isPublish && (
            <Field label="Publish to">
              <Select value={platform} onValueChange={setPlatform}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {platforms.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          )}

          <Field label="Date & time">
            <input
              type="datetime-local"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="w-full rounded-lg border border-fog bg-white px-3 py-2 text-[14px] text-ink outline-none focus:border-ash"
            />
          </Field>

          <Field label="Notes (optional)">
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Any instructions for this job…"
              className="w-full resize-none rounded-lg border border-fog bg-white px-3 py-2 text-[14px] text-ink outline-none focus:border-ash placeholder-steel"
              style={{ lineHeight: 1.5 }}
            />
          </Field>
        </div>

        <DialogFooter className="pt-4">
          <Button variant="outline" className="px-4 py-2 text-[13px]" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button className="px-4 py-2 text-[13px]" onClick={submit} disabled={creating}>
            {creating ? "Scheduling…" : "Schedule"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="mb-1.5 block text-[11px] font-medium tracking-tight-bold text-steel uppercase">
        {label}
      </label>
      {children}
    </div>
  );
}
