import { Play } from "lucide-react";
import type { GalleryItem } from "@/lib/api";

type MediaCardProps = {
  item: GalleryItem;
  className?: string;
  active?: boolean;
  priority?: boolean;
  onClick?: () => void;
};

export function MediaCard({ item, className = "", active = false, priority = false, onClick }: MediaCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group relative isolate h-full min-h-0 w-full overflow-hidden rounded-[18px] bg-[#111111] text-left ${
        active ? "ring-2 ring-[#d8ff63]" : "ring-1 ring-white/10"
      } ${className}`}
    >
      {item.media_kind === "image" ? (
        <img src={item.media_url} alt={item.title} className="h-full w-full object-cover transition duration-700 group-hover:scale-[1.03]" loading={priority ? "eager" : "lazy"} />
      ) : (
        <video
          src={item.media_url}
          className="h-full w-full object-cover transition duration-700 group-hover:scale-[1.03]"
          muted
          loop
          playsInline
          autoPlay={priority}
          preload="metadata"
          controls={priority}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/15 to-transparent" />
      <div className="absolute left-4 top-4 flex items-center gap-2">
        <span className="rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase text-[#101010]">
          {item.media_kind || item.kind}
        </span>
        {item.media_kind !== "image" ? (
          <span className="grid h-8 w-8 place-items-center rounded-full bg-[#d8ff63] text-[#101010]">
            <Play className="h-3.5 w-3.5 fill-current" />
          </span>
        ) : null}
      </div>
      <div className="absolute inset-x-0 bottom-0 p-5">
        <p className="line-clamp-1 text-[11px] font-semibold uppercase text-white/50">{item.story_title}</p>
        <h3 className="mt-2 line-clamp-2 text-[clamp(1.2rem,2vw,2.4rem)] font-semibold leading-[0.95] tracking-[-0.05em] text-white">
          {item.title}
        </h3>
      </div>
    </button>
  );
}

export function MediaGrid({
  items,
  selected,
  setSelected,
}: {
  items: GalleryItem[];
  selected: GalleryItem;
  setSelected: (id: string) => void;
}) {
  const cells = items.slice(0, 7);
  return (
    <div className="grid h-full min-h-[500px] grid-cols-12 grid-rows-[repeat(8,minmax(0,1fr))] gap-2 md:min-h-0">
      <div className="col-span-12 row-span-4 md:col-span-7 md:row-span-8">
        <MediaCard item={selected} active priority />
      </div>
      {cells.slice(0, 4).map((item) => (
        <div
          key={item.id}
          className="col-span-6 row-span-2 md:col-span-5 md:row-span-2"
        >
          <MediaCard item={item} active={item.id === selected.id} onClick={() => setSelected(item.id)} />
        </div>
      ))}
    </div>
  );
}
