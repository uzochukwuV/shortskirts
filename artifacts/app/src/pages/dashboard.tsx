import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useLocation } from "wouter";
import {
  ArrowRight,
  CalendarClock,
  ChevronRight,
  Clapperboard,
  Clock3,
  ExternalLink,
  Film,
  Layers3,
  RadioTower,
  Sparkles,
  Users2,
  Video,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api, type AutomationSchedule, type PublishTarget, type SocialAccount, type Story } from "@/lib/api";
import { CreateProductionDialog } from "@/components/create-production-dialog";
import { Button } from "@/components/ui/button";

function storyStatusTone(status: Story["status"]) {
  switch (status) {
    case "completed":
    case "ready":
      return "bg-[#d8ff63] text-[#101010]";
    case "generating":
      return "bg-[#101010] text-white";
    case "checkpoint_review":
      return "bg-[#f6f5ef] text-[#101010]";
    case "failed":
      return "bg-[#f3d2cf] text-[#7f2d24]";
    default:
      return "bg-[#ecebe4] text-[#5b5952]";
  }
}

function publishTone(status: string) {
  if (status === "published" || status === "processing") return "bg-[#d8ff63] text-[#101010]";
  if (status === "queued" || status === "ready") return "bg-[#101010] text-white";
  if (status === "failed" || status === "canceled") return "bg-[#f3d2cf] text-[#7f2d24]";
  return "bg-[#ecebe4] text-[#5b5952]";
}

function formatDate(value?: string | null) {
  if (!value) return "No date";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function DashboardHeader({ email }: { email?: string | null }) {
  return (
    <header className="sticky top-0 z-40 grid h-16 grid-cols-[1fr_auto] items-center border-b border-white/10 bg-[#0c0c0c]/82 px-4 backdrop-blur-xl md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-[#d8ff63] text-[#101010]">
            <Clapperboard className="h-4 w-4" />
          </span>
          <div className="leading-none">
            <div className="text-sm font-semibold tracking-[-0.03em] text-white">Dysentry</div>
            <div className="text-[11px] text-white/40">studio console</div>
          </div>
        </Link>
      </div>

      <div className="flex items-center gap-2">
        <Link href="/gallery" className="hidden rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-xs font-medium text-white/60 transition hover:bg-white/[0.08] hover:text-white md:inline-flex">
          Gallery
        </Link>
        <Link href="/pricing" className="hidden rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-xs font-medium text-white/60 transition hover:bg-white/[0.08] hover:text-white md:inline-flex">
          Pricing
        </Link>
        {email ? (
          <span className="hidden max-w-[240px] truncate rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-xs text-white/45 lg:inline-flex">
            {email}
          </span>
        ) : null}
      </div>
    </header>
  );
}

function SidebarStat({
  label,
  value,
  tone = "light",
}: {
  label: string;
  value: string;
  tone?: "light" | "dark";
}) {
  return (
    <div className={`rounded-[22px] border px-4 py-4 ${tone === "dark" ? "border-white/10 bg-white/[0.06] text-white" : "border-[#dbd9d0] bg-white text-[#101010]"}`}>
      <div className={`text-[11px] font-semibold uppercase ${tone === "dark" ? "text-white/45" : "text-[#75736b]"}`}>{label}</div>
      <div className="mt-3 text-3xl font-semibold leading-none tracking-[-0.06em]">{value}</div>
    </div>
  );
}

function StoryRow({ story }: { story: Story }) {
  return (
    <Link href={`/stories/${story.id}`} className="grid grid-cols-[1fr_auto] items-center gap-4 border-b border-[#e4e2d9] px-5 py-4 transition hover:bg-[#f7f6f0]">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${storyStatusTone(story.status)}`}>{story.status === "ready" ? "completed" : story.status}</span>
          <span className="rounded-full bg-[#ecebe4] px-2.5 py-1 text-[11px] font-semibold text-[#5b5952]">{story.workflow_type}</span>
        </div>
        <div className="mt-3 truncate text-lg font-semibold tracking-[-0.04em] text-[#101010]">{story.title}</div>
        <div className="mt-1 line-clamp-1 text-sm text-[#6f6d66]">{story.prompt}</div>
      </div>
      <div className="text-right">
        <div className="text-xs text-[#7a786f]">{formatDate(story.updated_at)}</div>
        <div className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-[#101010]">
          Open
          <ChevronRight className="h-4 w-4" />
        </div>
      </div>
    </Link>
  );
}

function ScheduleRow({ schedule }: { schedule: AutomationSchedule }) {
  return (
    <div className="rounded-[20px] border border-white/10 bg-white/[0.06] p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-white">{schedule.name}</div>
          <div className="mt-1 text-xs text-white/45">{schedule.schedule_type}</div>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${schedule.enabled ? "bg-[#d8ff63] text-[#101010]" : "bg-white/10 text-white/55"}`}>
          {schedule.enabled ? "active" : "paused"}
        </span>
      </div>
      <div className="mt-4 flex items-center justify-between text-xs text-white/50">
        <span>{schedule.cadence}</span>
        <span>{formatDate(schedule.next_run_at)}</span>
      </div>
    </div>
  );
}

function PublishRow({ publish }: { publish: PublishTarget }) {
  return (
    <div className="rounded-[20px] border border-[#dddacf] bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-[#101010]">{publish.title}</div>
          <div className="mt-1 text-xs text-[#727067]">{publish.platform} · {publish.asset_kind}</div>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${publishTone(publish.status)}`}>{publish.status}</span>
      </div>
      <div className="mt-4 flex items-center justify-between text-xs text-[#727067]">
        <span>{publish.publish_mode}</span>
        <span>{formatDate(publish.scheduled_for || publish.updated_at)}</span>
      </div>
    </div>
  );
}

function ChannelRow({ account }: { account: SocialAccount }) {
  return (
    <div className="flex items-center justify-between rounded-[18px] border border-[#dddacf] bg-white px-4 py-3">
      <div>
        <div className="text-sm font-semibold text-[#101010]">{account.display_name || account.platform}</div>
        <div className="mt-1 text-xs text-[#727067]">{account.platform}</div>
      </div>
      <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${account.status === "connected" ? "bg-[#d8ff63] text-[#101010]" : "bg-[#ecebe4] text-[#5b5952]"}`}>
        {account.status}
      </span>
    </div>
  );
}

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const { user } = useAuth();

  const { data: stories = [], isLoading: storiesLoading } = useQuery({
    queryKey: ["stories"],
    queryFn: api.getStories,
    refetchInterval: 6000,
  });
  const { data: schedules = [] } = useQuery({
    queryKey: ["schedules"],
    queryFn: api.getSchedules,
    refetchInterval: 10000,
  });
  const { data: publishTargets = [] } = useQuery({
    queryKey: ["publish-targets"],
    queryFn: api.getPublishTargets,
    refetchInterval: 10000,
  });
  const { data: socialAccounts = [] } = useQuery({
    queryKey: ["social-accounts"],
    queryFn: api.getSocialAccounts,
    refetchInterval: 15000,
  });

  const metrics = useMemo(() => {
    const activeStories = stories.filter((story) => story.status === "generating" || story.status === "checkpoint_review");
    const completedStories = stories.filter((story) => story.status === "completed" || story.status === "ready");
    const queuedPublishes = publishTargets.filter((target) => ["queued", "ready", "processing"].includes(target.status));
    const connectedChannels = socialAccounts.filter((account) => account.status === "connected");
    return {
      activeStories,
      completedStories,
      queuedPublishes,
      connectedChannels,
    };
  }, [stories, publishTargets, socialAccounts]);

  const recentStories = stories.slice(0, 8);
  const liveStories = metrics.activeStories.slice(0, 4);
  const upcomingSchedules = schedules.slice(0, 4);
  const publishQueue = publishTargets.slice(0, 5);
  const connectedChannels = socialAccounts.slice(0, 4);

  return (
    <main className="min-h-screen bg-[#0c0c0c] text-white">
      <DashboardHeader email={user?.email} />

      <div className="grid min-h-[calc(100vh-64px)] grid-cols-1 lg:grid-cols-[280px_1fr]">
        <aside className="border-b border-white/10 bg-[#0f0f0f] p-4 lg:border-b-0 lg:border-r lg:p-6">
          <div className="rounded-[28px] border border-white/10 bg-white/[0.04] p-5">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase text-white/45">
              <RadioTower className="h-3.5 w-3.5 text-[#d8ff63]" />
              Studio status
            </div>
            <h1 className="mt-4 text-[42px] font-semibold leading-[0.86] tracking-[-0.065em] text-white">
              Dashboard
            </h1>
            <p className="mt-3 text-sm leading-6 text-white/55">
              Productions, schedules, channels, and publish queue from the live backend.
            </p>
            <div className="mt-5">
              <CreateProductionDialog onCreated={(id) => setLocation(`/stories/${id}`)} />
            </div>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-1">
            <SidebarStat label="Productions" value={String(stories.length)} tone="dark" />
            <SidebarStat label="Active runs" value={String(metrics.activeStories.length)} tone="dark" />
            <SidebarStat label="Channels" value={String(metrics.connectedChannels.length)} tone="dark" />
            <SidebarStat label="Publish queue" value={String(metrics.queuedPublishes.length)} tone="dark" />
          </div>

          <div className="mt-4 rounded-[28px] border border-white/10 bg-white/[0.04] p-5">
            <div className="text-[11px] font-semibold uppercase text-white/45">Current focus</div>
            <div className="mt-4 grid gap-3">
              {[
                [Layers3, "Pipeline tracing", "Runs, steps, artifacts"],
                [CalendarClock, "Schedules", `${schedules.length} configured`],
                [Film, "Publishing", `${publishTargets.length} targets`],
              ].map(([Icon, title, detail]) => (
                <div key={title as string} className="flex items-center gap-3 rounded-[20px] border border-white/10 bg-white/[0.04] px-4 py-3">
                  <div className="grid h-10 w-10 place-items-center rounded-full bg-[#d8ff63] text-[#101010]">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">{title as string}</div>
                    <div className="text-xs text-white/45">{detail as string}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <section className="grid gap-4 bg-[#f6f5ef] p-4 text-[#101010] md:p-6">
          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-[32px] border border-[#dddacf] bg-white p-5 md:p-7">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-[11px] font-semibold uppercase text-[#7a786f]">Workspace overview</div>
                  <h2 className="mt-3 max-w-[720px] text-[clamp(2.8rem,5vw,5.2rem)] font-semibold leading-[0.82] tracking-[-0.07em]">
                    Build the next production, then route it through the pipeline.
                  </h2>
                </div>
                <Link href="/gallery" className="hidden shrink-0 rounded-full border border-[#dddacf] bg-[#f6f5ef] px-3 py-2 text-xs font-semibold text-[#5b5952] transition hover:bg-[#ecebe4] md:inline-flex">
                  Open gallery
                </Link>
              </div>

              <div className="mt-8 grid gap-3 md:grid-cols-4">
                <SidebarStat label="Drafts" value={String(stories.filter((story) => story.status === "draft").length)} />
                <SidebarStat label="Live runs" value={String(metrics.activeStories.length)} />
                <SidebarStat label="Completed" value={String(metrics.completedStories.length)} />
                <SidebarStat label="Schedules" value={String(schedules.length)} />
              </div>
            </div>

            <div className="rounded-[32px] border border-[#dddacf] bg-[#101010] p-5 text-white md:p-7">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] font-semibold uppercase text-white/45">Live pipeline</div>
                  <div className="mt-2 text-2xl font-semibold tracking-[-0.05em]">Active productions</div>
                </div>
                <span className="rounded-full bg-[#d8ff63] px-2.5 py-1 text-[11px] font-semibold text-[#101010]">
                  {metrics.activeStories.length}
                </span>
              </div>
              <div className="mt-6 grid gap-3">
                {liveStories.length > 0 ? (
                  liveStories.map((story) => (
                    <button
                      key={story.id}
                      type="button"
                      onClick={() => setLocation(`/stories/${story.id}`)}
                      className="grid grid-cols-[1fr_auto] items-center gap-4 rounded-[22px] border border-white/10 bg-white/[0.05] px-4 py-4 text-left transition hover:bg-white/[0.08]"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-white">{story.title}</div>
                        <div className="mt-1 text-xs text-white/45">{story.workflow_type}</div>
                      </div>
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${storyStatusTone(story.status)}`}>
                        {story.status}
                      </span>
                    </button>
                  ))
                ) : (
                  <div className="rounded-[22px] border border-white/10 bg-white/[0.05] px-4 py-8 text-sm text-white/50">
                    No active story jobs right now.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-[32px] border border-[#dddacf] bg-white">
              <div className="flex items-center justify-between border-b border-[#e4e2d9] px-5 py-4">
                <div>
                  <div className="text-[11px] font-semibold uppercase text-[#7a786f]">Productions</div>
                  <div className="mt-1 text-lg font-semibold tracking-[-0.04em]">Recent stories</div>
                </div>
                <span className="text-xs text-[#7a786f]">{storiesLoading ? "Loading" : `${recentStories.length} shown`}</span>
              </div>
              <div>
                {recentStories.length > 0 ? (
                  recentStories.map((story) => <StoryRow key={story.id} story={story} />)
                ) : (
                  <div className="px-5 py-12 text-sm text-[#7a786f]">No productions yet.</div>
                )}
              </div>
            </div>

            <div className="grid gap-4">
              <div className="rounded-[32px] border border-[#dddacf] bg-[#101010] p-5 text-white md:p-6">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase text-white/45">
                  <CalendarClock className="h-3.5 w-3.5 text-[#d8ff63]" />
                  Schedules
                </div>
                <div className="mt-5 grid gap-3">
                  {upcomingSchedules.length > 0 ? (
                    upcomingSchedules.map((schedule) => <ScheduleRow key={schedule.id} schedule={schedule} />)
                  ) : (
                    <div className="rounded-[20px] border border-white/10 bg-white/[0.05] px-4 py-8 text-sm text-white/50">
                      No schedules configured yet.
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-[32px] border border-[#dddacf] bg-white p-5 md:p-6">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase text-[#7a786f]">
                  <Film className="h-3.5 w-3.5 text-[#101010]" />
                  Publish queue
                </div>
                <div className="mt-5 grid gap-3">
                  {publishQueue.length > 0 ? (
                    publishQueue.map((publish) => <PublishRow key={publish.id} publish={publish} />)
                  ) : (
                    <div className="rounded-[20px] border border-[#dddacf] bg-[#f6f5ef] px-4 py-8 text-sm text-[#7a786f]">
                      No publish targets yet.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-[32px] border border-[#dddacf] bg-white p-5 md:p-6">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase text-[#7a786f]">
                <Users2 className="h-3.5 w-3.5 text-[#101010]" />
                Connected channels
              </div>
              <div className="mt-5 grid gap-3">
                {connectedChannels.length > 0 ? (
                  connectedChannels.map((account) => <ChannelRow key={account.id} account={account} />)
                ) : (
                  <div className="rounded-[20px] border border-[#dddacf] bg-[#f6f5ef] px-4 py-8 text-sm text-[#7a786f]">
                    No social accounts connected yet.
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[32px] border border-[#dddacf] bg-white p-5 md:p-6">
              <div className="text-[11px] font-semibold uppercase text-[#7a786f]">Quick actions</div>
              <div className="mt-5 grid gap-3 md:grid-cols-3">
                {[
                  {
                    icon: Video,
                    title: "Open latest story",
                    text: recentStories[0] ? recentStories[0].title : "No story yet",
                    action: () => recentStories[0] && setLocation(`/stories/${recentStories[0].id}`),
                  },
                  {
                    icon: CalendarClock,
                    title: "Review schedules",
                    text: schedules.length ? `${schedules.length} configured` : "No schedules",
                    action: () => {},
                  },
                  {
                    icon: ExternalLink,
                    title: "Browse output",
                    text: "See public gallery assets",
                    action: () => setLocation("/gallery"),
                  },
                ].map((card) => (
                  <button
                    key={card.title}
                    type="button"
                    onClick={card.action}
                    className="rounded-[24px] border border-[#dddacf] bg-[#f6f5ef] p-5 text-left transition hover:bg-[#ecebe4]"
                  >
                    <div className="grid h-11 w-11 place-items-center rounded-full bg-white text-[#101010]">
                      <card.icon className="h-4 w-4" />
                    </div>
                    <div className="mt-6 text-lg font-semibold tracking-[-0.04em] text-[#101010]">{card.title}</div>
                    <div className="mt-2 text-sm leading-6 text-[#706f66]">{card.text}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

