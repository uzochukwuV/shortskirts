import { Link } from "wouter";
import {
  ArrowRight,
  Bot,
  Check,
  ChevronRight,
  Clock3,
  Code2,
  Film,
  Layers3,
  Play,
  RadioTower,
  Route,
  Sparkles,
  Wand2,
} from "lucide-react";
import type { GalleryItem } from "@/lib/api";
import { Button } from "@/components/ui/button";

const requestRows = [
  ["outline-agent", "iad", "1,240 ms"],
  ["qwen-video-router", "sin", "8,420 ms"],
  ["cosyvoice-narration", "fra", "96 ms"],
  ["publish-scheduler", "edge", "310 ms"],
];

const benefits = [
  {
    label: "Designed for",
    title: "AI showrunners",
    text: "Prompt, references, script, scenes, narration, and publish settings move through one pipeline.",
    points: ["No tool sprawl", "No lost state", "Human approvals built in"],
  },
  {
    label: "Engineered for",
    title: "Model fallback",
    text: "The coordinator can route failed scene attempts to another provider and keep the production moving.",
    points: ["Provider attempts traced", "Task IDs stored", "Retry policy per step"],
  },
  {
    label: "Built for",
    title: "Recurring channels",
    text: "Schedules can generate only, publish existing media, or generate and publish after approval.",
    points: ["Series continuation", "YouTube/TikTok layer", "Publish queue isolation"],
  },
];

const stats = [
  ["1", "pipeline API"],
  ["3", "approval gates"],
  ["5", "worker workloads"],
  ["24/7", "scheduled runs"],
];

const pipeline = [
  ["01", "Requests", "A story brief, image references, cast notes, schedule, or publish command enters Dysentry."],
  ["02", "Planning", "The coordinator turns user intent into outline, scene plan, provider route, and checkpoints."],
  ["03", "Execution", "Workers render scenes, narrate audio, assemble episodes, and record every attempt."],
  ["04", "Delivery", "Users approve the result, schedule future runs, or publish completed media."],
];

function MiniMedia({ item }: { item: GalleryItem }) {
  return (
    <div className="relative h-full min-h-[280px] overflow-hidden rounded-[28px] bg-[#101010]">
      {item.media_kind === "image" ? (
        <img src={item.media_url} alt={item.title} className="h-full w-full object-cover" />
      ) : (
        <video src={item.media_url} className="h-full w-full object-cover" muted loop playsInline autoPlay preload="metadata" />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent" />
      <div className="absolute bottom-4 left-4 right-4">
        <div className="text-[11px] font-semibold uppercase text-white/50">{item.story_title}</div>
        <div className="mt-1 line-clamp-2 text-2xl font-semibold leading-[0.95] tracking-[-0.05em] text-white">{item.title}</div>
      </div>
    </div>
  );
}

function RequestPanel() {
  return (
    <div className="grid h-full min-h-[500px] content-between border-l border-[#d9d8d0] bg-[#101010] p-5 text-white md:p-8">
      <div>
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <div className="text-[11px] font-semibold uppercase text-white/45">Generation</div>
            <div className="mt-1 text-sm text-white">last 60s</div>
          </div>
          <div className="flex items-center gap-2 rounded-full bg-[#d8ff63] px-3 py-1.5 text-xs font-semibold text-[#101010]">
            <RadioTower className="h-3.5 w-3.5" />
            live
          </div>
        </div>

        <div className="mt-6 grid gap-3">
          {requestRows.map(([model, region, latency]) => (
            <div key={model} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded-[18px] border border-white/10 bg-white/[0.045] px-4 py-3">
              <div className="min-w-0 truncate text-sm text-white">{model}</div>
              <div className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] uppercase text-white/50">{region}</div>
              <div className="font-mono text-xs text-[#d8ff63]">{latency}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-[24px] border border-white/10 bg-white/[0.045] p-4">
        <div className="flex items-center gap-2 text-xs text-white/45">
          <Code2 className="h-3.5 w-3.5" />
          POST /pipeline/stories/:id/generate
        </div>
        <pre className="mt-4 overflow-hidden text-xs leading-6 text-white/70">
{`{
  "media": "video",
  "ratio": "9:16",
  "fallback": true,
  "checkpoint_batch": 3
}`}
        </pre>
      </div>
    </div>
  );
}

export function RunwareLanding({ items, isAuthenticated }: { items: GalleryItem[]; isAuthenticated: boolean }) {
  const heroItem = items[0];
  const sampleItems = items.slice(0, 3);

  return (
    <div className="min-h-screen w-full bg-[#f6f5ef] pt-16 text-[#101010]">
      <section className="grid min-h-[calc(100vh-64px)] border-b border-[#d9d8d0] lg:grid-cols-[1fr_520px]">
        <div className="grid content-between p-5 md:p-10">
          <div className="flex flex-wrap gap-2">
            {["Video", "Image stories", "Voice", "Scheduling", "Publishing"].map((item) => (
              <span key={item} className="rounded-full border border-[#d9d8d0] bg-white px-3 py-1.5 text-xs font-semibold text-[#5e5d57]">
                {item}
              </span>
            ))}
          </div>

          <div className="py-12 md:py-16">
            <h1 className="max-w-[1040px] text-[clamp(4.4rem,10vw,11.5rem)] font-semibold leading-[0.78] tracking-[-0.08em]">
              One pipeline for AI shows.
            </h1>
            <p className="mt-7 max-w-[720px] text-[clamp(1.35rem,2vw,2.2rem)] font-medium leading-[1.05] tracking-[-0.045em] text-[#3f3e39]">
              We orchestrate while you publish.
            </p>
            <p className="mt-5 max-w-[680px] text-base leading-7 text-[#706f66]">
              Dysentry turns story ideas into approved scenes, assembled episodes, scheduled continuations, and platform-ready uploads.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href={isAuthenticated ? "/dashboard" : "/login"}>
                <Button size="lg" className="rounded-full bg-[#101010] px-6 text-white hover:bg-[#2a2a2a]">
                  Go live in hours
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/gallery">
                <Button size="lg" variant="outline" className="rounded-full border-[#bdbbb0] bg-white px-6 text-[#101010] hover:bg-[#ecebe4]">
                  View gallery
                  <Play className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {stats.map(([value, label]) => (
              <div key={label} className="border-t border-[#d9d8d0] pt-4">
                <div className="text-[clamp(2rem,4vw,4rem)] font-semibold leading-none tracking-[-0.07em]">{value}</div>
                <div className="mt-2 text-xs leading-4 text-[#706f66]">{label}</div>
              </div>
            ))}
          </div>
        </div>

        <RequestPanel />
      </section>

      <section className="grid border-b border-[#d9d8d0] lg:grid-cols-3">
        {benefits.map((item) => (
          <article key={item.title} className="grid min-h-[420px] content-between border-b border-[#d9d8d0] bg-[#f6f5ef] p-6 md:p-10 lg:border-b-0 lg:border-r">
            <div>
              <div className="text-sm font-semibold text-[#77766d]">{item.label}</div>
              <h2 className="mt-3 text-[clamp(3rem,5vw,5.8rem)] font-semibold leading-[0.82] tracking-[-0.075em]">{item.title}</h2>
              <p className="mt-5 max-w-[460px] text-sm leading-6 text-[#706f66]">{item.text}</p>
            </div>
            <div className="grid gap-2">
              {item.points.map((point) => (
                <div key={point} className="flex items-center gap-2 text-sm text-[#3f3e39]">
                  <span className="grid h-5 w-5 place-items-center rounded-full bg-[#101010] text-white">
                    <Check className="h-3 w-3" />
                  </span>
                  {point}
                </div>
              ))}
            </div>
          </article>
        ))}
      </section>

      <section className="grid border-b border-[#d9d8d0] lg:grid-cols-[420px_1fr]">
        <div className="border-b border-[#d9d8d0] p-6 md:p-10 lg:border-b-0 lg:border-r">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#101010] text-[#d8ff63]">
            <Film className="h-5 w-5" />
          </div>
          <h2 className="mt-10 text-[clamp(3.2rem,5vw,6rem)] font-semibold leading-[0.82] tracking-[-0.075em]">
            Any series. Any scene.
          </h2>
          <p className="mt-5 text-sm leading-6 text-[#706f66]">
            Every completed video or image scene can become a gallery proof, a scheduled asset, or a publish target.
          </p>
          <Link href="/gallery" className="mt-8 inline-flex items-center gap-2 text-sm font-semibold">
            Browse generated media
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="grid min-h-[520px] grid-cols-1 gap-2 bg-[#101010] p-2 md:grid-cols-3">
          {sampleItems.map((item) => (
            <MiniMedia key={item.id} item={item} />
          ))}
        </div>
      </section>

      <section className="grid border-b border-[#d9d8d0] lg:grid-cols-[1fr_1fr]">
        <div className="grid content-between border-b border-[#d9d8d0] p-6 md:p-10 lg:border-b-0 lg:border-r">
          <div>
            <Route className="h-8 w-8" />
            <h2 className="mt-12 max-w-[760px] text-[clamp(3.7rem,7vw,8rem)] font-semibold leading-[0.78] tracking-[-0.08em]">
              Request → Plan → Execute → Deliver.
            </h2>
          </div>
          <p className="mt-8 max-w-[620px] text-base leading-7 text-[#706f66]">
            This is the product advantage: users do not just generate one clip. They operate a traceable media pipeline.
          </p>
        </div>

        <div className="grid">
          {pipeline.map(([number, title, text]) => (
            <div key={number} className="grid grid-cols-[80px_1fr] border-b border-[#d9d8d0]">
              <div className="border-r border-[#d9d8d0] p-5 text-sm font-semibold text-[#706f66] md:p-7">{number}</div>
              <div className="p-5 md:p-7">
                <h3 className="text-3xl font-semibold leading-none tracking-[-0.06em]">{title}</h3>
                <p className="mt-3 max-w-[560px] text-sm leading-6 text-[#706f66]">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid min-h-[440px] place-items-center bg-[#101010] p-6 text-center text-white md:p-10">
        <div>
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#d8ff63] text-[#101010]">
            <Wand2 className="h-5 w-5" />
          </div>
          <h2 className="mt-8 max-w-[980px] text-[clamp(4rem,8vw,9rem)] font-semibold leading-[0.78] tracking-[-0.08em]">
            Build the channel before the audience arrives.
          </h2>
          <Link href={isAuthenticated ? "/dashboard" : "/login"} className="mt-8 inline-flex">
            <Button size="lg" className="rounded-full bg-white px-7 text-[#101010] hover:bg-white/90">
              Start with Dysentry
              <Sparkles className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}

