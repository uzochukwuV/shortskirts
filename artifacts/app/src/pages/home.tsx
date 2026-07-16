import { useMemo, useRef } from "react";
import { Link } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, Briefcase, BookOpen, ChevronLeft, ChevronRight, Clock, Film, Gamepad2, Layers, Play, Sparkles, TrendingUp, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Layout } from "@/components/layout";
import { api, GalleryItem } from "@/lib/api";

const ICPs = [
  {
    icon: Users,
    who: "Indie creators",
    title: "Make a series people recognize",
    text: "Persisted characters, repeatable formats, and scene-level regeneration for weekly output.",
  },
  {
    icon: Briefcase,
    who: "Agencies",
    title: "Move briefs through approval fast",
    text: "Brand bibles, storyboard review, and asset reuse for multiple clients without starting over.",
  },
  {
    icon: BookOpen,
    who: "Educators",
    title: "Turn lessons into explainers",
    text: "Structure lessons into episodes, then render a consistent visual sequence from the same brief.",
  },
  {
    icon: Gamepad2,
    who: "IP and game teams",
    title: "Keep characters consistent",
    text: "Use the same story world across trailers, lore drops, teasers, and campaign assets.",
  },
];

const STEPS = [
  { n: "01", title: "Write the brief", text: "Drop in a campaign, lesson, or series idea. The outline expands from one source of truth." },
  { n: "02", title: "Approve the plan", text: "Review the episode structure before any render runs. Fix the story once, not after the cost." },
  { n: "03", title: "Generate scenes", text: "Render scenes independently so one failure does not block the whole episode." },
  { n: "04", title: "Export and reuse", text: "Re-run individual scenes, keep the cast memory, and publish the next episode faster." },
];

const TEMPLATES = [
  { tag: "Brand", label: "Product launch" },
  { tag: "Creator", label: "Serialized fiction" },
  { tag: "Social", label: "Short-form hooks" },
  { tag: "Education", label: "Lesson explainer" },
  { tag: "Game", label: "Lore teaser" },
  { tag: "Studio", label: "Client campaign" },
];

const FEATURES = [
  {
    title: "Memory across episodes",
    text: "Characters, tone, and brand details persist instead of resetting every run.",
  },
  {
    title: "Approval gates",
    text: "Outline approval happens before render. Scene review happens before export.",
  },
  {
    title: "Queue-backed generation",
    text: "Jobs can retry, lease, and report progress without blocking the interface.",
  },
];

function GalleryCarousel({ items }: { items: GalleryItem[] }) {
  const railRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: "left" | "right") => {
    const rail = railRef.current;
    if (!rail) return;
    const amount = Math.min(rail.clientWidth * 0.88, 560);
    rail.scrollBy({ left: direction === "left" ? -amount : amount, behavior: "smooth" });
  };

  return (
    <section className="mx-auto max-w-[1200px] px-4 py-16 md:px-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 rounded-[12px] border border-border bg-white px-3 py-1 text-[11px] font-medium uppercase text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-[color:#ff5a00]" />
            Latest renders
          </div>
          <h2 className="mt-4 text-3xl font-semibold text-foreground">Generated videos from the database</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Recent scene clips and assembled episodes pulled from live production records.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => scroll("left")} aria-label="Scroll videos left">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => scroll("right")} aria-label="Scroll videos right">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div
        ref={railRef}
        className="mt-8 flex gap-4 overflow-x-auto scroll-smooth pb-2 [scrollbar-width:none] [-ms-overflow-style:none]"
        style={{ scrollSnapType: "x mandatory" }}
      >
        {items.map((item) => (
          <article
            key={item.id}
            className="min-w-[82vw] max-w-[82vw] shrink-0 snap-start md:min-w-[420px] md:max-w-[420px]"
          >
            <div className="overflow-hidden rounded-[36px] border border-border bg-white">
              <div className="border-b border-border bg-muted/40 px-5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-[11px] uppercase text-muted-foreground">{item.story_title}</div>
                    <h3 className="mt-1 text-lg font-semibold text-foreground">{item.title}</h3>
                  </div>
                  <Badge className="border-0 bg-[color:#ff5a00] text-white">
                    {item.kind}
                  </Badge>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                  <span className="rounded-[10000px] border border-border bg-white px-2.5 py-1">
                    Ep {item.episode_number}
                    {item.scene_number ? ` · Sc ${item.scene_number}` : ""}
                  </span>
                  <span className="rounded-[10000px] border border-border bg-white px-2.5 py-1">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="bg-foreground p-3">
                {item.media_kind === "image" ? (
                  <img
                    className="aspect-video w-full rounded-[24px] bg-black object-cover"
                    src={item.media_url}
                    alt={item.title}
                    loading="lazy"
                  />
                ) : (
                  <video
                    className="aspect-video w-full rounded-[24px] bg-black object-cover"
                    src={item.media_url}
                    controls
                    muted
                    loop
                    playsInline
                    preload="metadata"
                  />
                )}
              </div>

              <div className="space-y-3 p-5">
                <p className="text-sm leading-6 text-muted-foreground line-clamp-3">
                  {item.summary || "Generated media from a completed production step."}
                </p>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{item.media_kind === "image" ? (item.duration ? `${Math.round(item.duration)}s still` : "Image scene") : (item.duration ? `${Math.round(item.duration)}s` : "Video clip")}</span>
                  <a href={item.media_url} target="_blank" rel="noreferrer" className="font-medium text-foreground hover:underline">
                    Open source file
                  </a>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function Home() {
  const { data: galleryItems = [] } = useQuery({
    queryKey: ["gallery", "public"],
    queryFn: api.getPublicGallery,
    staleTime: 30_000,
  });

  const visibleGallery = useMemo(() => galleryItems.filter((item) => item.media_url), [galleryItems]);

  return (
    <Layout>
      <div className="bg-background">
        <section className="border-b border-border">
          <div className="mx-auto grid max-w-[1200px] gap-10 px-4 py-16 md:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:py-20">
            <div className="space-y-7">
              <div className="inline-flex items-center gap-2 rounded-[12px] border border-border bg-white px-3 py-1.5 text-[12px] font-medium text-foreground">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[color:#ff5a00] text-white">
                  <Sparkles className="h-3 w-3" />
                </span>
                Serialized video production
              </div>

              <div className="space-y-4">
                <h1 className="max-w-3xl text-5xl font-semibold leading-[1.08] tracking-tight text-foreground md:text-6xl">
                  Not a clip generator.
                  <span className="block">A series engine for teams that ship weekly.</span>
                </h1>
                <p className="max-w-2xl text-[15px] leading-7 text-muted-foreground">
                  StoryForge turns one brief into an approved outline, scene plan, and generated episode.
                  It is built for recurring production, not one-off demos.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Link href="/dashboard">
                  <Button size="lg" className="w-full sm:w-auto">
                    Start a production <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link href="/pricing">
                  <Button size="lg" variant="outline" className="w-full sm:w-auto">
                    View pricing
                  </Button>
                </Link>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  ["Approval before render", "Outline-first workflow"],
                  ["Scene-level retries", "No full rerun needed"],
                  ["Persistent cast", "Characters stay consistent"],
                ].map(([label, sub]) => (
                  <div key={label} className="rounded-[24px] border border-border bg-white p-4">
                    <div className="text-sm font-medium text-foreground">{label}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{sub}</div>
                  </div>
                ))}
              </div>
            </div>

            <Card className="overflow-hidden">
              <div className="border-b border-border bg-muted/40 p-7">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-[11px] uppercase text-muted-foreground">Current production</div>
                    <h2 className="mt-2 text-2xl font-semibold text-foreground">Project Atlas</h2>
                    <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
                      Product brief is approved. Three scenes are queued. One failure can retry without blocking the episode.
                    </p>
                  </div>
                  <Badge className="bg-[color:#ff5a00] text-white border-0">Outline approved</Badge>
                </div>
              </div>
              <CardContent className="space-y-5 p-7">
                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    ["Draft", "Brief locked"],
                    ["Queue", "3 scenes pending"],
                    ["Export", "Vertical cut"],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-[24px] border border-border bg-background p-4">
                      <div className="text-[11px] uppercase text-muted-foreground">{label}</div>
                      <div className="mt-2 text-sm font-medium text-foreground">{value}</div>
                    </div>
                  ))}
                </div>

                <div className="rounded-[28px] border border-border bg-white p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-[11px] uppercase text-muted-foreground">Workflow</div>
                      <div className="mt-1 text-lg font-semibold text-foreground">Brief to episode</div>
                    </div>
                    <div className="inline-flex items-center gap-1 rounded-[12px] border border-border bg-muted px-3 py-1 text-xs text-foreground">
                      <Clock className="h-3.5 w-3.5" /> 8 min
                    </div>
                  </div>
                  <div className="mt-5 space-y-3">
                    {[
                      "Story plan written",
                      "Characters approved",
                      "Scene render leased",
                      "Episode ready to export",
                    ].map((step, index) => (
                      <div key={step} className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-muted text-xs font-medium text-foreground">
                          {index + 1}
                        </div>
                        <div className="flex-1 rounded-[14px] border border-border bg-background px-4 py-2 text-sm text-foreground">
                          {step}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-[28px] border border-border bg-background p-5">
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <Play className="h-4 w-4 text-[color:#ff5a00]" />
                      Preview render
                    </div>
                    <div className="mt-4 aspect-[16/10] rounded-[24px] border border-dashed border-border bg-white p-4">
                      <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                        Storyboard, clip, and approval state live here.
                      </div>
                    </div>
                  </div>
                  <div className="rounded-[28px] border border-border bg-background p-5">
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <BadgeCheck className="h-4 w-4 text-[color:#ff5a00]" />
                      Release notes
                    </div>
                    <div className="mt-4 space-y-3">
                      {[
                        "Job leasing prevents duplicate renders.",
                        "Retries are per-step, not whole-run.",
                        "Worker heartbeats keep the queue visible.",
                      ].map((line) => (
                        <div key={line} className="rounded-[14px] border border-border bg-white px-4 py-3 text-sm text-muted-foreground">
                          {line}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {visibleGallery.length > 0 && (
          <GalleryCarousel items={visibleGallery} />
        )}

        <section className="mx-auto max-w-[1200px] px-4 py-16 md:px-6">
          <div className="flex items-end justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 rounded-[12px] border border-border bg-white px-3 py-1 text-[11px] font-medium uppercase text-muted-foreground">
                <Briefcase className="h-3.5 w-3.5 text-[color:#ff5a00]" />
                ICP
              </div>
              <h2 className="mt-4 text-3xl font-semibold text-foreground">Who this is for</h2>
            </div>
            <Link href="/pricing" className="hidden items-center gap-2 text-sm font-medium text-foreground md:inline-flex">
              See plans <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {ICPs.map((item) => {
              const Icon = item.icon;
              return (
                <Card key={item.who}>
                  <CardContent className="space-y-4 p-7">
                    <div className="flex h-10 w-10 items-center justify-center rounded-[14px] border border-border bg-muted text-foreground">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="text-[11px] uppercase text-muted-foreground">{item.who}</div>
                      <h3 className="mt-2 text-lg font-semibold text-foreground">{item.title}</h3>
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">{item.text}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>

        <section className="bg-foreground text-background">
          <div className="mx-auto max-w-[1200px] px-4 py-16 md:px-6">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-[12px] border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-medium uppercase text-background/70">
                <Layers className="h-3.5 w-3.5 text-[color:#ff5a00]" />
                Product edge
              </div>
              <h2 className="mt-4 text-3xl font-semibold">Built around the workflow, not the output button</h2>
            </div>
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {FEATURES.map((feature) => (
                <div key={feature.title} className="rounded-[28px] border border-white/10 bg-white/5 p-6">
                  <h3 className="text-lg font-semibold">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-background/70">{feature.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1200px] px-4 py-16 md:px-6">
          <div className="flex items-end justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 rounded-[12px] border border-border bg-white px-3 py-1 text-[11px] font-medium uppercase text-muted-foreground">
                <Film className="h-3.5 w-3.5 text-[color:#ff5a00]" />
                Templates
              </div>
              <h2 className="mt-4 text-3xl font-semibold text-foreground">Production templates</h2>
            </div>
            <Link href="/dashboard" className="hidden items-center gap-2 text-sm font-medium text-foreground md:inline-flex">
              Open dashboard <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {TEMPLATES.map((template) => (
              <Link key={template.label} href="/dashboard">
                <Card className="group h-full transition-colors hover:border-foreground">
                  <CardContent className="space-y-4 p-7">
                    <div className="inline-flex items-center rounded-[12px] border border-border bg-muted px-3 py-1 text-[11px] font-medium uppercase text-foreground">
                      {template.tag}
                    </div>
                    <h3 className="text-lg font-semibold text-foreground group-hover:underline">{template.label}</h3>
                    <p className="text-sm leading-6 text-muted-foreground">
                      Start from a structure that already fits the format.
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-[1200px] px-4 pb-16 md:px-6">
          <div className="rounded-[36px] border border-border bg-white p-8 md:p-10">
            <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
              <div className="max-w-2xl">
                <div className="inline-flex items-center gap-2 rounded-[12px] border border-border bg-muted px-3 py-1 text-[11px] font-medium uppercase text-muted-foreground">
                  <TrendingUp className="h-3.5 w-3.5 text-[color:#ff5a00]" />
                  Positioning
                </div>
                <h2 className="mt-4 text-3xl font-semibold text-foreground">A series engine is the sharper sell.</h2>
                <p className="mt-4 text-sm leading-6 text-muted-foreground">
                  The market is crowded with AI video generators. The wedge here is consistency, approvals, and a repeatable production loop for recurring content.
                </p>
              </div>
              <Link href="/pricing">
                <Button variant="outline">
                  Review plans <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}
