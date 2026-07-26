import React, { useEffect, useState, useCallback } from "react";
import { Plus, CalendarClock } from "lucide-react";

import { useToast } from "@/components/ui/use-toast";
import AppChrome from "@/components/dysentry/AppChrome";
import Button from "@/components/dysentry/Button";
import ScheduleForm from "@/components/dysentry/schedule/ScheduleForm";
import ScheduledJobCard from "@/components/dysentry/schedule/ScheduledJobCard";
import { deleteSchedule, listSchedules, listStories } from "@/api/dysentryClient";

export default function Schedule() {
  const { toast } = useToast();
  const [jobs, setJobs] = useState([]);
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [storyList, scheduleList] = await Promise.all([
        listStories(),
        listSchedules(),
      ]);
      setStories(storyList);
      setJobs(scheduleList);
    } catch (error) {
      toast({ title: "Could not load schedules", description: error.message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCancel = async (job) => {
    try {
      await deleteSchedule(job.id);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      toast({ title: "Schedule removed" });
    } catch (error) {
      toast({ title: "Could not cancel", description: error.message, variant: "destructive" });
    }
  };

  const seriesTitle = (id) => stories.find((story) => story.id === id)?.title;

  return (
    <AppChrome
      breadcrumb={[{ label: "Studio", path: "/dashboard" }, { label: "Schedule" }]}
      actions={
        <Button className="px-5 py-2.5 text-[14px]" onClick={() => setFormOpen(true)}>
          <Plus className="h-4 w-4" /> New job
        </Button>
      }
    >
      <div className="mx-auto max-w-3xl px-8 py-10">
        <h1 className="font-display mb-1 text-[26px] font-medium text-ink">Schedule</h1>
        <p className="mb-10 text-[14px] text-steel" style={{ lineHeight: 1.5 }}>
          Automate generation, series continuation, and publish windows against the live backend scheduler.
        </p>

        {loading ? (
          <p className="text-[14px] text-steel">Loading…</p>
        ) : jobs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-fog py-16 text-center">
            <CalendarClock className="mx-auto h-8 w-8 text-ash" />
            <p className="mt-3 text-[14px] text-steel">No scheduled jobs yet.</p>
            <button
              onClick={() => setFormOpen(true)}
              className="mt-2 text-[14px] text-signal transition-colors hover:text-[#1557b8]"
            >
              Schedule your first job
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <ScheduledJobCard
                key={job.id}
                job={job}
                seriesTitle={seriesTitle(job.story_id)}
                onCancel={handleCancel}
              />
            ))}
          </div>
        )}
      </div>

      <ScheduleForm open={formOpen} onOpenChange={setFormOpen} series={stories} onCreated={load} />
    </AppChrome>
  );
}
