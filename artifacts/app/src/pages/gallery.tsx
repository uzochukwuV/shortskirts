import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Film } from "lucide-react";
import { Link } from "wouter";
import { api } from "@/lib/api";
import { fallbackGallery } from "@/components/landing/landing-data";
import { LandingNav } from "@/components/landing/landing-nav";
import { MediaCard } from "@/components/landing/media-card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export default function Gallery() {
  const { isAuthenticated } = useAuth();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: galleryItems = [] } = useQuery({
    queryKey: ["gallery", "public"],
    queryFn: api.getPublicGallery,
    staleTime: 30_000,
    retry: 1,
  });

  const items = useMemo(() => {
    const live = galleryItems.filter((item) => item.media_url);
    return live.length ? live : fallbackGallery;
  }, [galleryItems]);
  const selected = items.find((item) => item.id === selectedId) ?? items[0];

  return (
    <main className="min-h-screen bg-[#080808] text-white">
      <LandingNav />

      <section className="grid min-h-[520px] border-b border-white/10 pt-16 lg:grid-cols-[0.82fr_1.18fr]">
        <div className="grid content-end border-b border-white/10 p-6 pb-10 md:p-10 lg:border-b-0 lg:border-r">
          <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-xs text-white/65">
            <Film className="h-3.5 w-3.5 text-[#d8ff63]" />
            Public gallery
          </div>
          <h1 className="max-w-[820px] text-[clamp(4rem,8vw,9rem)] font-semibold leading-[0.78] tracking-[-0.075em]">
            Generated work from Dysentry.
          </h1>
        </div>
        <div className="min-h-[520px] p-2">
          <MediaCard item={selected} active priority />
        </div>
      </section>

      <section className="grid border-b border-white/10 lg:grid-cols-[360px_1fr]">
        <aside className="border-b border-white/10 p-6 md:p-10 lg:border-b-0 lg:border-r">
          <p className="text-sm font-semibold text-white/45">Browse</p>
          <h2 className="mt-4 text-[clamp(3rem,5vw,5.6rem)] font-semibold leading-[0.82] tracking-[-0.07em]">
            Scenes and episodes.
          </h2>
          <p className="mt-5 text-sm leading-6 text-white/55">
            These assets are pulled from the backend public gallery endpoint, so unauthenticated visitors can see what the system can produce.
          </p>
          <Link href={isAuthenticated ? "/dashboard" : "/login"} className="mt-8 inline-flex">
            <Button className="rounded-full bg-[#d8ff63] px-6 text-[#101010] hover:bg-[#e4ff8c]">
              Create yours
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </aside>

        <div className="grid auto-rows-[360px] grid-cols-1 gap-2 p-2 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <MediaCard key={item.id} item={item} active={item.id === selected.id} onClick={() => setSelectedId(item.id)} />
          ))}
        </div>
      </section>
    </main>
  );
}

