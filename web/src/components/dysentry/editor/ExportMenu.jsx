import React, { useState } from "react";
import { ChevronDown, Download } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

const platforms = [
  { id: "tiktok", label: "TikTok", ratio: "9:16" },
  { id: "reels", label: "Reels", ratio: "9:16" },
  { id: "youtube_shorts", label: "YT Shorts", ratio: "9:16" },
  { id: "stories", label: "Stories", ratio: "9:16" },
];

export default function ExportMenu({ onExport }) {
  const [selected, setSelected] = useState(["tiktok", "reels"]);
  const [open, setOpen] = useState(false);

  const toggle = (id) => {
    setSelected((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );
  };

  const handleExport = () => {
    onExport?.(selected);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button className="inline-flex items-center gap-2 rounded-lg bg-signal px-4 py-2 text-[13px] text-white shadow-subtle transition-colors hover:bg-[#1557b8]">
          <Download className="h-4 w-4" />
          Export
          <ChevronDown className="h-3.5 w-3.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-56 p-2">
        <div className="space-y-1">
          {platforms.map((platform) => (
            <label
              key={platform.id}
              className="flex cursor-pointer items-center justify-between rounded-md px-2 py-2 transition-colors hover:bg-muted"
            >
              <span className="text-[14px] text-ink">{platform.label}</span>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-steel">{platform.ratio}</span>
                <input
                  type="checkbox"
                  checked={selected.includes(platform.id)}
                  onChange={() => toggle(platform.id)}
                  className="accent-signal"
                />
              </div>
            </label>
          ))}
        </div>
        <button
          onClick={handleExport}
          className="mt-2 w-full rounded-md bg-ink px-3 py-2 text-[13px] text-white transition-colors hover:bg-[#1f2937]"
        >
          Export selected
        </button>
      </PopoverContent>
    </Popover>
  );
}
