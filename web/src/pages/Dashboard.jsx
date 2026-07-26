import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CalendarClock, PlayCircle, TrendingUp, Workflow, Plus } from "lucide-react";
import AppChrome from "@/components/dysentry/AppChrome";
import Button from "@/components/dysentry/Button";
import { Image } from "@/components/ui/image";
import CreateStoryModal from "@/components/dysentry/CreateStoryModal";
import { AreaChart, Area, XAxis, ResponsiveContainer, Tooltip } from "recharts";
import {
  listSchedules,
  listSocialAccounts,
  listStories,
  getDashboardBatch,
} from "@/api/dysentryClient";

export default function Dashboard() {
  const [stories, setStories] = useState([]);
  const [episodes, setEpisodes] = useState([]);
  const [runs, setRuns] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        // Use batch endpoint to avoid N+1 queries
        const [scheduleList, accountList, storyList] = await Promise.all([
          listSchedules(),
          listSocialAccounts(),
          listStories(),
        ]);

        // Then batch load episodes and runs for all stories
        let batchData = { episodes: [], runs: [] };
        if (storyList.length > 0) {
          batchData = await getDashboardBatch(storyList.map((s) => s.id));
        }

        setStories(storyList);
        setSchedules(scheduleList);
        setAccounts(accountList);
        setEpisodes(batchData.episodes);
        setRuns(batchData.runs);
      } catch (loadError) {
        setError(loadError.message || "Could not load dashboard");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const pending = episodes.filter((episode) =>
    new Set(["draft", "approved", "checkpoint_review"]).has(episode.status),
  );
  const completedEpisodes = episodes.filter((episode) => episode.status === "completed");
  const activeRuns = runs.filter((run) => run.status === "running" || run.status === "pending");
  const failedRuns = runs.filter((run) => run.status === "failed");
  const connectedAccounts = accounts.filter((account) => account.status === "connected");
  const latestStory = stories[0] || null;
  // Chart shows episode completion status - green for completed, amber for pending
  const chartData = episodes.slice(0, 8).map((episode) => ({
    ep: `E${String(episode.episode_number).padStart(2, "0")}`,
    status: episode.status === "completed" ? "done" : "pending",
    // Note: Analytics data would come from a dedicated analytics endpoint
    views: episode.assembled_video_url ? null : null, // Placeholder for real analytics
  }));
  const latestRuns = [...runs]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);
  const nextSchedules = schedules
    .filter((schedule) => schedule.enabled)
    .sort((a, b) => new Date(a.next_run_at || 0).getTime() - new Date(b.next_run_at || 0).getTime())
    .slice(0, 4);

  const stats = [
    { label: "Stories", value: stories.length },
    { label: "Episodes completed", value: completedEpisodes.length },
    { label: "Active runs", value: activeRuns.length },
    { label: "Connected channels", value: connectedAccounts.length },
  ];

  // Refresh stories after creating a new one
  const handleStoryCreated = () => {
    setCreateModalOpen(false);
    // Refresh the stories list
    listStories().then(setStories).catch(() => {});
  };

  return (
    <AppChrome
      breadcrumb={[{ label: "Studio" }, { label: "Dashboard" }]}
      actions={
        <>
          <Button 
            variant="primary"
            onClick={() => setCreateModalOpen(true)}
            className="px-5 py-2.5 text-[14px]"
          >
            <Plus className="h-4 w-4 mr-1" />
            New Story
          </Button>
          <Link to="/schedule">
            <Button className="px-5 py-2.5 text-[14px]">Open schedule</Button>
          </Link>
        </>
      }
    >
      <div className="mx-auto max-w-[1280px] px-8 py-10">
        <div className="mb-8 grid gap-6 lg:grid-cols-[1.7fr_1fr]">
          <div className="rounded-lg border border-fog bg-paper p-6">
            <p className="text-[11px] uppercase tracking-[0.12em] text-steel">Studio snapshot</p>
            <h1 className="mt-3 font-display text-[30px] font-medium text-ink">
              {latestStory ? latestStory.title : "No stories yet"}
            </h1>
            <p className="mt-3 max-w-2xl text-[14px] text-steel" style={{ lineHeight: 1.6 }}>
              {latestStory?.description || "Continue a story from the editor, or use schedule and publishing to automate release."}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              {latestStory ? (
                <Link to={`/editor/${latestStory.id}`}>
                  <Button>
                    Open latest story <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              ) : (
                <Link to="/">
                  <Button>
                    Go to landing <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              )}
              <Link to="/settings">
                <Button variant="secondary">Channels & settings</Button>
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
            <SummaryCard icon={Workflow} label="Pipeline failures" value={failedRuns.length} helper="Recent failed runs" />
            <SummaryCard icon={CalendarClock} label="Scheduled automations" value={schedules.length} helper="Configured jobs" />
            <SummaryCard icon={PlayCircle} label="Render-ready episodes" value={completedEpisodes.length} helper="Assembled outputs" />
          </div>
        </div>

        {/* Stats */}
        <div className="grid gap-px overflow-hidden rounded-lg border border-mist sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="bg-paper p-6">
              <p className="text-[11px] text-steel">{s.label}</p>
              <p className="font-display mt-2 text-[26px] font-medium text-ink">{s.value}</p>
            </div>
          ))}
        </div>

        {/* Analytics + pending */}
        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          <div className="rounded-lg border border-fog p-6 lg:col-span-2">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <p className="text-[11px] text-steel">Episode completion signal</p>
                <h3 className="text-[16px] font-medium text-ink">Assembly coverage</h3>
              </div>
              <TrendingUp className="h-4 w-4 text-steel" />
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="views" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#1a73e8" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#1a73e8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="ep"
                  tick={{ fontSize: 11, fill: "#576579" }}
                  axisLine={{ stroke: "#e7eaee" }}
                  tickLine={false}
                />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #dbdfe5", fontSize: 13 }} />
                <Area type="monotone" dataKey="views" stroke="#1a73e8" strokeWidth={2} fill="url(#views)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="rounded-lg border border-fog p-6">
            <h3 className="mb-4 text-[16px] font-medium text-ink">Needs attention</h3>
            {pending.length === 0 ? (
              <p className="text-[13px] text-steel">No episodes currently waiting on review.</p>
            ) : (
              <div className="space-y-3">
                {pending.slice(0, 5).map((e) => (
                  <Link
                    key={e.id}
                    to={`/editor/${e.series_id}`}
                    className="block rounded-lg border border-fog p-3 transition-colors hover:border-ash"
                  >
                    <p className="text-[14px] font-medium text-ink">{e.title}</p>
                    <p className="mt-0.5 text-[11px] text-steel">Episode {e.episode_number} · {e.status.replaceAll("_", " ")}</p>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          <div className="rounded-lg border border-fog p-6 lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-[16px] font-medium text-ink">Recent pipeline runs</h2>
              <span className="text-[12px] text-steel">{runs.length} total</span>
            </div>
            {latestRuns.length === 0 ? (
              <p className="text-[13px] text-steel">No generation runs recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {latestRuns.map((run) => (
                  <div key={run.id} className="flex items-center justify-between rounded-lg border border-fog px-4 py-3">
                    <div>
                      <p className="text-[14px] font-medium text-ink">{run.run_type.replaceAll("_", " ")}</p>
                      <p className="mt-0.5 text-[12px] text-steel">
                        {(run.workflow_version || "workflow")} · {new Date(run.created_at).toLocaleString()}
                      </p>
                    </div>
                    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${runStatusClass(run.status)}`}>
                      {run.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-fog p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-[16px] font-medium text-ink">Upcoming schedules</h2>
              <CalendarClock className="h-4 w-4 text-steel" />
            </div>
            {nextSchedules.length === 0 ? (
              <p className="text-[13px] text-steel">No active schedules yet.</p>
            ) : (
              <div className="space-y-3">
                {nextSchedules.map((schedule) => (
                  <div key={schedule.id} className="rounded-lg border border-fog px-4 py-3">
                    <p className="text-[14px] font-medium text-ink">{schedule.name}</p>
                    <p className="mt-0.5 text-[12px] text-steel">
                      {schedule.schedule_type.replaceAll("_", " ")} · {schedule.next_run_at ? new Date(schedule.next_run_at).toLocaleString() : "Not scheduled"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Story grid */}
        <div className="mt-12">
          <h2 className="font-display mb-6 text-[20px] font-medium text-ink">Your stories</h2>
          {loading ? (
            <p className="text-[14px] text-steel">Loading…</p>
          ) : error ? (
            <p className="text-[14px] text-destructive">{error}</p>
          ) : stories.length === 0 ? (
            <p className="text-[14px] text-steel">No stories yet. Create your first one from the landing flow.</p>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {stories.map((s) => (
                <Link
                  key={s.id}
                  to={`/editor/${s.id}`}
                  className="group rounded-lg border border-fog p-4 transition-colors hover:border-ash"
                >
                  <div className="overflow-hidden rounded-2xl">
                    {s.cover_image ? (
                      <Image src={s.cover_image} alt={s.title} className="aspect-video w-full object-cover" fittingType="fill" />
                    ) : (
                      <div className="aspect-video w-full rounded-2xl bg-muted" />
                    )}
                  </div>
                  <div className="mt-4 flex items-center justify-between gap-3">
                    <p className="text-[11px] capitalize text-steel">{s.status?.replace("_", " ")}</p>
                    <p className="text-[11px] capitalize text-steel">{s.workflow_type?.replaceAll("_", " ")}</p>
                  </div>
                  <h3 className="mt-1 text-[16px] text-ink">{s.title}</h3>
                  {s.description && (
                    <p className="mt-1 line-clamp-2 text-[13px] text-steel" style={{ lineHeight: 1.5 }}>{s.description}</p>
                  )}
                  <div className="mt-4 inline-flex items-center gap-1 text-[13px] text-ink group-hover:text-signal">
                    Open editor <ArrowRight className="h-3.5 w-3.5" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <CreateStoryModal
        open={createModalOpen}
        onOpenChange={(open) => {
          setCreateModalOpen(open);
          if (!open) {
            // Refresh stories when modal closes
            listStories().then(setStories).catch(() => {});
          }
        }}
      />
    </AppChrome>
  );
}

function SummaryCard({ icon: Icon, label, value, helper }) {
  return (
    <div className="rounded-lg border border-fog bg-paper p-5">
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-steel">{label}</p>
        <Icon className="h-4 w-4 text-steel" />
      </div>
      <p className="mt-2 font-display text-[26px] font-medium text-ink">{value}</p>
      <p className="mt-1 text-[12px] text-steel">{helper}</p>
    </div>
  );
}

function runStatusClass(status) {
  if (status === "completed") return "border-emerald-200 text-emerald-700";
  if (status === "failed") return "border-red-200 text-red-700";
  if (status === "running") return "border-blue-200 text-blue-700";
  return "border-fog text-steel";
}
