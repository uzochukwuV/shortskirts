import { Link } from "wouter";
import { ArrowRight, Bot, CalendarClock, Play, Sparkles } from "lucide-react";
import type { GalleryItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { MediaGrid } from "./media-card";
import { consoleStats } from "./landing-data";

const heroFeatures = [
  { icon: Bot, title: "Model router", text: "Retry failed scenes through the next best provider." },
  { icon: CalendarClock, title: "Scheduler", text: "Generate only, publish existing, or generate and publish." },
  { icon: Sparkles, title: "Human checkpoints", text: "Approve batches before the next execution continues." },
];

export function LandingHero({
  items,
  selected,
  setSelected,
  isAuthenticated,
}: {
  items: GalleryItem[];
  selected: GalleryItem;
  setSelected: (id: string) => void;
  isAuthenticated: boolean;
}) {
  return (
    <section className="relative overflow-hidden bg-[#080808] pt-16 text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(216,255,99,0.20),transparent_28%),radial-gradient(circle_at_82%_8%,rgba(255,255,255,0.12),transparent_24%)]" />
      <div className="relative grid w-full grid-cols-1 lg:grid-cols-[0.92fr_1.08fr]">
        <div className="grid min-h-[520px] grid-rows-[1fr_auto] border-b border-white/10 bg-white/[0.035] p-5 md:min-h-[calc(100vh-168px)] md:p-10 lg:border-b-0 lg:border-r">
          <div className="flex flex-col justify-center">
            <div className="mb-5 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-xs font-medium text-white/70">
                <Sparkles className="h-3.5 w-3.5 text-[#d8ff63]" />
                AI showrunner OS
              </span>
              <span className="rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-xs text-white/55">
                Qwen-powered pipeline
              </span>
            </div>

            <h1 className="max-w-[780px] text-[clamp(3.7rem,7.6vw,8.2rem)] font-semibold leading-[0.79] tracking-[-0.075em]">
              Dysentry creates the next episode.
            </h1>
            <p className="mt-6 max-w-[640px] text-base leading-7 text-white/62">
              A production workspace for generated series: prompts become outlines, characters, scenes, narration,
              scheduled runs, and publish-ready episodes.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <Link href={isAuthenticated ? "/dashboard" : "/login"}>
                <Button size="lg" className="rounded-full bg-[#d8ff63] px-6 text-[#101010] hover:bg-[#e4ff8c]">
                  Start a production
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <a href="#gallery">
                <Button size="lg" variant="outline" className="rounded-full border-white/14 bg-white/8 px-6 text-white hover:bg-white/12">
                  Watch samples
                  <Play className="h-4 w-4" />
                </Button>
              </a>
            </div>
          </div>

          <div className="mt-8 grid grid-cols-3 gap-3 border-t border-white/10 pt-4">
            {consoleStats.map(([value, label]) => (
              <div key={label}>
                <div className="text-2xl font-semibold tracking-[-0.05em] text-white">{value}</div>
                <div className="mt-1 text-xs leading-4 text-white/45">{label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="min-h-[520px] border-b border-white/10 bg-white/[0.035] p-2 md:min-h-[calc(100vh-168px)] lg:border-b-0">
          <MediaGrid items={items} selected={selected} setSelected={setSelected} />
        </div>
      </div>

      <div className="relative grid border-y border-white/10 text-white/58 md:grid-cols-3">
        {heroFeatures.map(({ icon: Icon, title, text }) => (
          <div key={title} className="grid grid-cols-[auto_1fr] gap-4 border-white/10 p-5 md:border-r md:p-6">
            <div className="grid h-11 w-11 place-items-center rounded-full bg-white/8 text-[#d8ff63]">
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <div className="font-semibold text-white">{title}</div>
              <div className="mt-1 text-sm leading-6">{text}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
