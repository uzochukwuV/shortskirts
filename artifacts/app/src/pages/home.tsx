import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { ArrowRight, ChevronLeft, ChevronRight, Clock, Play, Sparkles, Video } from "lucide-react";
import { api, GalleryItem } from "@/lib/api";
import { Layout } from "@/components/layout";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";

function ReelCard({ item, active, onClick }: { item: GalleryItem; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group min-w-[240px] max-w-[240px] shrink-0 snap-start rounded-[16px] border bg-white text-left transition-all ${
        active ? "border-[color:#083300] shadow-[0_0_0_1px_rgba(8,51,0,0.18)]" : "border-border hover:border-[color:#96ff1a]"
      }`}
    >
      <div className="relative aspect-[4/5] overflow-hidden rounded-[16px]">
        {item.media_kind === "image" ? (
          <img src={item.media_url} alt={item.title} className="h-full w-full object-cover" loading="lazy" />
        ) : (
          <video src={item.media_url} className="h-full w-full object-cover" muted playsInline preload="metadata" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent" />
        <div className="absolute left-3 top-3 flex items-center gap-2">
          <Badge className="border-0 bg-white/90 text-[color:#083300]">{item.kind}</Badge>
        </div>
        <div className="absolute bottom-3 left-3 right-3">
          <div className="text-[11px] uppercase tracking-[0.14em] text-white/70">{item.story_title}</div>
          <div className="mt-1 line-clamp-2 text-base font-semibold text-white">{item.title}</div>
        </div>
      </div>
    </button>
  );
}

export default function Home() {
  const { isAuthenticated } = useAuth();
  const railRef = useRef<HTMLDivElement | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: galleryItems = [] } = useQuery({
    queryKey: ["gallery", "public"],
    queryFn: api.getPublicGallery,
    staleTime: 30_000,
  });

  const items = useMemo(
    () => galleryItems.filter((item) => item.media_url),
    [galleryItems],
  );
  const selected = items.find((item) => item.id === selectedId) ?? items[0] ?? null;

  const scroll = (dir: "left" | "right") => {
    const el = railRef.current;
    if (!el) return;
    el.scrollBy({ left: dir === "left" ? -560 : 560, behavior: "smooth" });
  };

  return (
    <Layout>
      <div className="bg-white">
        <section className="space-y-6">
          <PageHeader
            eyebrow="Public reel"
            title="Stories, scenes, and voice-led motion in one production console."
            description="Browse finished scenes, open the studio, and keep the full workflow in one place. The public gallery is backed by live production data."
            actions={
              <>
                <Link href={isAuthenticated ? "/dashboard" : "/login"}>
                  <Button size="lg" variant="lime">
                    {isAuthenticated ? "Open studio" : "Start workspace"}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link href="/pricing">
                  <Button size="lg" variant="outline">
                    View plans
                  </Button>
                </Link>
              </>
            }
          />

          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-[24px] border border-border bg-[color:#121212] p-4 text-white">
              <div className="flex items-center justify-between gap-3 border-b border-white/10 px-2 pb-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-white/55">Featured render</div>
                  <div className="mt-1 text-lg font-semibold">{selected?.title || "No public reel yet"}</div>
                </div>
                <Badge className="border-0 bg-[color:#96ff1a] text-[color:#083300]">{selected?.kind || "scene"}</Badge>
              </div>
              <div className="mt-3 overflow-hidden rounded-[14px] bg-black">
                {selected ? (
                  selected.media_kind === "image" ? (
                    <img src={selected.media_url} alt={selected.title} className="aspect-video w-full object-cover" />
                  ) : (
                    <video src={selected.media_url} className="aspect-video w-full object-cover" controls muted playsInline />
                  )
                ) : (
                  <div className="flex aspect-video items-center justify-center">
                    <Video className="h-10 w-10 text-white/30" />
                  </div>
                )}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="rounded-[14px] border border-white/10 bg-white/5 px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-white/45">Story</div>
                  <div className="mt-1 line-clamp-1 text-sm text-white">{selected?.story_title || "Public gallery"}</div>
                </div>
                <div className="rounded-[14px] border border-white/10 bg-white/5 px-4 py-3">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-white/45">Created</div>
                  <div className="mt-1 text-sm text-white">
                    {selected ? new Date(selected.created_at).toLocaleDateString() : "Live"}
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-4">
              <div className="rounded-[24px] border border-border bg-white p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">What users get</div>
                <div className="mt-3 space-y-4 text-sm leading-6 text-foreground">
                  <div className="flex items-start gap-3">
                    <Clock className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                    <span>Outline, approval, and generation in one flow.</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <Video className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                    <span>Scene boxes on top, preview on the right, audio below.</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <Sparkles className="mt-0.5 h-4 w-4 text-[color:#083300]" />
                    <span>Public samples pulled from live production data.</span>
                  </div>
                </div>
              </div>

              <div className="rounded-[24px] border border-border bg-white p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Selected sample</div>
                <div className="mt-3 rounded-[16px] border border-border bg-muted/30 p-4">
                  <div className="text-sm font-semibold text-foreground">{selected?.story_title || "Public gallery"}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{selected ? new Date(selected.created_at).toLocaleDateString() : "Live"}</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6">
          <div className="flex items-end justify-between gap-4">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Generated reel</div>
              <h2 className="mt-2 font-display text-[40px] leading-[1] tracking-[-0.04em] text-foreground">
                From the database, not a mockup.
              </h2>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="icon" onClick={() => scroll("left")} aria-label="Scroll left">
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={() => scroll("right")} aria-label="Scroll right">
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div
            ref={railRef}
            className="mt-6 flex gap-4 overflow-x-auto pb-2 [scrollbar-width:none] [-ms-overflow-style:none]"
            style={{ scrollSnapType: "x mandatory" }}
          >
            {items.map((item) => (
              <ReelCard
                key={item.id}
                item={item}
                active={item.id === selected?.id}
                onClick={() => setSelectedId(item.id)}
              />
            ))}
          </div>
        </section>

        <section className="mt-8 border-t border-border bg-muted/30">
          <div className="mx-auto grid max-w-[1200px] gap-6 px-4 py-12 md:px-6 lg:grid-cols-[1fr_1fr_1fr]">
            {[
              {
                title: "Outline to render",
                text: "Build the story, approve the plan, then generate scenes and audio without leaving the workspace.",
              },
              {
                title: "Preview with context",
                text: "Select any scene box, inspect the media, and keep the current version visible while you edit the next one.",
              },
              {
                title: "Human checkpoints",
                text: "Pause after batches, approve narration, and continue without losing the production state.",
              },
            ].map((item) => (
              <div key={item.title} className="rounded-[16px] border border-border bg-white p-5">
                <div className="text-sm font-semibold text-foreground">{item.title}</div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.text}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </Layout>
  );
}
