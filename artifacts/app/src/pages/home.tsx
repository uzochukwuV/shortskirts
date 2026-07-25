import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { LandingNav } from "@/components/landing/landing-nav";
import { fallbackGallery } from "@/components/landing/landing-data";
import { RunwareLanding } from "@/components/landing/runware-landing";

export default function Home() {
  const { isAuthenticated } = useAuth();
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

  return (
    <main className="min-h-screen w-full overflow-x-hidden bg-[#f6f5ef] font-sans">
      <LandingNav />
      <RunwareLanding items={items} isAuthenticated={isAuthenticated} />
    </main>
  );
}

