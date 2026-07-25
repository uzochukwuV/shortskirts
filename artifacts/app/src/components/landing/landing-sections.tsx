import { ArrowRight, CheckCircle2, ChevronLeft, ChevronRight, Film, Layers3, Wand2 } from "lucide-react";
import { Link } from "wouter";
import type { GalleryItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { workflowCards } from "./landing-data";
import { MediaCard } from "./media-card";

export function WorkflowSection() {
  return (
    <section className="grid w-full grid-cols-1 border-b border-[#e7e7e7] bg-white lg:grid-cols-[1fr_1.2fr]">
      <div className="border-b border-[#e7e7e7] p-6 md:p-10 lg:border-b-0 lg:border-r">
        <p className="text-sm font-semibold text-[#707070]">Composable pipeline</p>
        <h2 className="mt-4 max-w-[720px] text-[clamp(3rem,6vw,6.5rem)] font-semibold leading-[0.82] tracking-[-0.07em] text-[#101010]">
          Built like a control room, not a prompt box.
        </h2>
        <p className="mt-6 max-w-[640px] text-base leading-7 text-[#707070]">
          The product is moving toward an agent-led workflow where generation, approval, retries, scheduling, and publishing are all traceable steps.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2">
        {workflowCards.map((card) => (
          <div key={card.eyebrow} className="min-h-[280px] border-b border-[#e7e7e7] p-6 md:border-r md:p-8 even:md:border-r-0">
            <div className="text-xs font-semibold text-[#707070]">{card.eyebrow}</div>
            <h3 className="mt-14 text-[clamp(2.2rem,4vw,4.8rem)] font-semibold leading-[0.82] tracking-[-0.07em] text-[#101010]">
              {card.title}
            </h3>
            <p className="mt-5 max-w-[360px] text-sm leading-6 text-[#707070]">{card.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function GallerySection({
  items,
  selectedId,
  setSelected,
  onScroll,
}: {
  items: GalleryItem[];
  selectedId: string;
  setSelected: (id: string) => void;
  onScroll: (direction: "left" | "right") => void;
}) {
  return (
    <section id="gallery" className="bg-[#080808] text-white">
      <div className="grid border-b border-white/10 lg:grid-cols-[420px_1fr]">
        <div className="border-b border-white/10 bg-white/[0.035] p-6 md:p-10 lg:border-b-0 lg:border-r">
          <p className="text-sm font-semibold text-white/45">Generated gallery</p>
          <h2 className="mt-4 text-[clamp(3rem,5vw,5.8rem)] font-semibold leading-[0.82] tracking-[-0.07em]">
            Real renders from the system.
          </h2>
          <p className="mt-5 text-sm leading-6 text-white/55">
            This surface is backed by `/pipeline/gallery/public`, so it can show the videos and scenes users are paying for.
          </p>
          <div className="mt-8 flex gap-2">
            <Button size="icon" variant="outline" className="rounded-full border-white/12 bg-white/8 text-white hover:bg-white/12" onClick={() => onScroll("left")}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button size="icon" variant="outline" className="rounded-full border-white/12 bg-white/8 text-white hover:bg-white/12" onClick={() => onScroll("right")}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="overflow-hidden bg-white/[0.035] p-2">
          <div data-gallery-rail className="grid auto-cols-[minmax(260px,360px)] grid-flow-col gap-2 overflow-x-auto [scrollbar-width:none]">
            {items.map((item) => (
              <div key={item.id} className="h-[500px]">
                <MediaCard item={item} active={item.id === selectedId} onClick={() => setSelected(item.id)} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function StudioSection({ isAuthenticated }: { isAuthenticated: boolean }) {
  return (
    <section className="grid w-full grid-cols-1 bg-[#f6f6f3] lg:grid-cols-2">
      <div className="min-h-[620px] border-b border-[#deded8] p-6 md:p-10 lg:border-b-0 lg:border-r">
        <Film className="h-8 w-8 text-[#101010]" />
        <h2 className="mt-16 max-w-[760px] text-[clamp(3.5rem,7vw,7.5rem)] font-semibold leading-[0.8] tracking-[-0.075em] text-[#101010]">
          Schedule a channel, not a task.
        </h2>
      </div>
      <div className="grid content-between gap-10 p-6 md:p-10">
        <div className="grid gap-3">
          {[
            "Upload style, character, and scene references before generation.",
            "Approve outline and scene batches before the agent continues.",
            "Publish completed episodes manually or from schedules.",
          ].map((item) => (
            <div key={item} className="grid grid-cols-[auto_1fr] gap-3 rounded-[24px] border border-[#deded8] bg-white p-5">
              <CheckCircle2 className="mt-0.5 h-5 w-5 text-[#101010]" />
              <p className="text-sm leading-6 text-[#505050]">{item}</p>
            </div>
          ))}
        </div>
        <div className="rounded-[30px] bg-[#101010] p-6 text-white">
          <Layers3 className="h-6 w-6 text-[#d8ff63]" />
          <h3 className="mt-10 text-4xl font-semibold leading-[0.9] tracking-[-0.06em]">A console for long-running productions.</h3>
          <Link href={isAuthenticated ? "/dashboard" : "/login"} className="mt-8 inline-flex">
            <Button className="rounded-full bg-[#d8ff63] px-6 text-[#101010] hover:bg-[#e4ff8c]">
              Open Dysentry
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}

export function ClosingBand({ isAuthenticated }: { isAuthenticated: boolean }) {
  return (
    <section className="grid min-h-[360px] place-items-center border-t border-white/10 bg-[#080808] px-4 py-16 text-center text-white">
      <div>
        <Wand2 className="mx-auto h-7 w-7 text-[#d8ff63]" />
        <h2 className="mt-6 max-w-[920px] text-[clamp(3.4rem,7vw,8rem)] font-semibold leading-[0.78] tracking-[-0.075em]">
          Start the next recurring story.
        </h2>
        <Link href={isAuthenticated ? "/dashboard" : "/login"} className="mt-8 inline-flex">
          <Button size="lg" className="rounded-full bg-white px-7 text-[#101010] hover:bg-white/90">
            Enter studio
            <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
      </div>
    </section>
  );
}
