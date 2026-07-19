import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useLocation } from "wouter";
import { ArrowRight, CheckCircle2, Clock, FolderKanban, Gauge, Sparkles, Video } from "lucide-react";
import { Layout } from "@/components/layout";
import { PageHeader } from "@/components/page-header";
import { CreateProductionDialog } from "@/components/create-production-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, Story } from "@/lib/api";

function statusTone(status: Story["status"]) {
  switch (status) {
    case "draft":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "approved":
      return "border-border bg-muted text-foreground";
    case "generating":
      return "border-[color:#96ff1a] bg-[color:#f5ffd8] text-[color:#083300]";
    case "checkpoint_review":
      return "border-[color:#96ff1a] bg-white text-[color:#083300]";
    case "completed":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    default:
      return "border-border bg-white text-foreground";
  }
}

function statusLabel(status: Story["status"]) {
  return status === "ready" ? "completed" : status;
}

function StoryCard({ story }: { story: Story }) {
  return (
    <Link href={`/stories/${story.id}`} className="block">
      <article className="group rounded-[16px] border border-border bg-white p-5 transition-all hover:border-[color:#083300]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className={`inline-flex items-center rounded-[9999px] border px-2.5 py-1 text-[11px] font-medium ${statusTone(story.status)}`}>
              {statusLabel(story.status)}
            </div>
            <h3 className="mt-3 truncate text-[20px] font-display leading-[1] tracking-[-0.04em] text-foreground">
              {story.title}
            </h3>
          </div>
          <div className="rounded-[9999px] border border-border bg-muted px-2.5 py-1 text-[11px] text-muted-foreground">
            {story.workflow_type}
          </div>
        </div>

        <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">{story.prompt}</p>

        <div className="mt-5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
          <span className="rounded-[9999px] border border-border bg-muted px-2.5 py-1">
            {story.workflow_version || "v1"}
          </span>
          <span className="rounded-[9999px] border border-border bg-muted px-2.5 py-1">
            {story.generation_version || "v1"}
          </span>
          <span className="rounded-[9999px] border border-border bg-muted px-2.5 py-1">
            {story.approval_status}
          </span>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-border pt-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5" />
            {new Date(story.created_at).toLocaleDateString()}
          </span>
          <span className="inline-flex items-center gap-1 text-foreground group-hover:translate-x-0.5 transition-transform">
            Open
            <ArrowRight className="h-3.5 w-3.5" />
          </span>
        </div>
      </article>
    </Link>
  );
}

export default function Dashboard() {
  const [, setLocation] = useLocation();
  const { data: stories = [], isLoading } = useQuery({
    queryKey: ["stories"],
    queryFn: api.getStories,
    refetchInterval: (query) =>
      query.state.data?.some((story: Story) => story.status === "generating" || story.status === "checkpoint_review")
        ? 6000
        : false,
  });

  const metrics = useMemo(() => {
    const total = stories.length;
    const drafts = stories.filter((story) => story.status === "draft").length;
    const active = stories.filter((story) => story.status === "generating" || story.status === "checkpoint_review").length;
    const complete = stories.filter((story) => story.status === "completed" || story.status === "ready").length;
    return { total, drafts, active, complete };
  }, [stories]);

  const activeStories = stories
    .filter((story) => story.status === "generating" || story.status === "checkpoint_review")
    .slice(0, 4);

  const recentStories = stories.slice(0, 6);

  return (
    <Layout>
      <div className="bg-white">
        <section className="space-y-6">
          <PageHeader
            eyebrow="Studio index"
            title="Production dashboard for stories that already exist in the backend."
            description="Briefs, approvals, version history, and render state are all exposed here. Open a story to work the console."
            actions={<CreateProductionDialog onCreated={(id) => setLocation(`/stories/${id}`)} />}
            stats={[
              { label: "Total productions", value: String(metrics.total), hint: "All stories in the workspace." },
              { label: "Drafts", value: String(metrics.drafts), hint: "Awaiting approval or edits." },
              { label: "Active", value: String(metrics.active), hint: "Currently generating." },
              { label: "Completed", value: String(metrics.complete), hint: "Ready for review." },
            ]}
          />
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-4">
            <div className="flex items-end justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Recent productions</div>
                <h2 className="mt-2 font-display text-[40px] leading-[1] tracking-[-0.04em] text-foreground">
                  Open a story to enter the console.
                </h2>
              </div>
              <div className="text-sm text-muted-foreground">
                {isLoading ? "Loading..." : `${recentStories.length} shown`}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {recentStories.length > 0 ? (
                recentStories.map((story) => <StoryCard key={story.id} story={story} />)
              ) : (
                <div className="rounded-[16px] border border-dashed border-border bg-muted/30 p-8 text-sm text-muted-foreground md:col-span-2">
                  No productions yet. Create one from the studio button.
                </div>
              )}
            </div>
          </div>

          <aside className="space-y-4">
            <div className="rounded-[16px] border border-border bg-[color:#121212] p-5 text-white">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-white/60">
                <Gauge className="h-3.5 w-3.5 text-[color:#96ff1a]" />
                Live queue
              </div>
              <div className="mt-3 space-y-3">
                {activeStories.length > 0 ? activeStories.map((story) => (
                  <button
                    key={story.id}
                    type="button"
                    onClick={() => setLocation(`/stories/${story.id}`)}
                    className="w-full rounded-[14px] border border-white/10 bg-white/5 px-4 py-3 text-left transition-colors hover:bg-white/10"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-white">{story.title}</div>
                        <div className="mt-1 text-xs text-white/60">{story.workflow_type}</div>
                      </div>
                      <Badge className="border-0 bg-[color:#96ff1a] text-[color:#083300]">
                        {statusLabel(story.status)}
                      </Badge>
                    </div>
                  </button>
                )) : (
                  <div className="rounded-[14px] border border-white/10 bg-white/5 px-4 py-6 text-sm text-white/60">
                    No active jobs.
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[16px] border border-border bg-white p-5">
              <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Session notes</div>
              <div className="mt-3 space-y-3 text-sm leading-6 text-foreground">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                  <span>Scene and checkpoint versioning is already exposed.</span>
                </div>
                <div className="flex items-start gap-3">
                  <Video className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                  <span>Open a story to see the video console with scene boxes and narration.</span>
                </div>
                <div className="flex items-start gap-3">
                  <Sparkles className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                  <span>Create the next production from the button above.</span>
                </div>
              </div>
            </div>
          </aside>
        </section>
      </div>
    </Layout>
  );
}
