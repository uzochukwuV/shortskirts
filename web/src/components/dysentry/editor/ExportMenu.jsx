import React, { useState } from "react";
import { ChevronDown, Download, Loader2, Check } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { exportEpisode } from "@/api/dysentryClient";

const platforms = [
  { id: "tiktok", label: "TikTok", ratio: "9:16", icon: "🎵" },
  { id: "reels", label: "Instagram Reels", ratio: "9:16", icon: "📱" },
  { id: "youtube_shorts", label: "YT Shorts", ratio: "9:16", icon: "▶️" },
  { id: "stories", label: "Stories", ratio: "9:16", icon: "📖" },
];

export default function ExportMenu({ episode, loading, onExportStart, onExportComplete }) {
  const [selected, setSelected] = useState(["tiktok"]);
  const [exporting, setExporting] = useState(false);
  const [exportedPlatforms, setExportedPlatforms] = useState([]);
  const [open, setOpen] = useState(false);

  const toggle = (id) => {
    if (exportedPlatforms.includes(id)) return; // Can't unselect already exported
    setSelected((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );
  };

  const handleExport = async () => {
    if (!episode || selected.length === 0) return;
    
    setExporting(true);
    onExportStart?.(selected);
    
    const results = [];
    for (const platform of selected) {
      try {
        await exportEpisode(episode.id, platform);
        results.push({ platform, success: true });
        setExportedPlatforms((prev) => [...prev, platform]);
      } catch (error) {
        results.push({ platform, success: false, error: error.message });
      }
    }
    
    setExporting(false);
    onExportComplete?.(results);
    setSelected([]); // Clear selection after export
  };

  const allExported = platforms.every((p) => exportedPlatforms.includes(p.id));

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button 
          disabled={!episode}
          className="inline-flex items-center gap-2 rounded-lg bg-signal px-4 py-2 text-[13px] text-white shadow-subtle transition-colors hover:bg-[#1557b8] disabled:opacity-50"
        >
          {exporting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Export
          <ChevronDown className="h-3.5 w-3.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 p-3">
        <div className="mb-3">
          <p className="text-sm font-medium text-ink">Export Episode</p>
          <p className="text-xs text-steel mt-0.5">Select platforms to export to</p>
        </div>
        
        <div className="space-y-1">
          {platforms.map((platform) => {
            const isSelected = selected.includes(platform.id);
            const isExported = exportedPlatforms.includes(platform.id);
            
            return (
              <label
                key={platform.id}
                className={`flex cursor-pointer items-center justify-between rounded-md px-3 py-2.5 transition-colors ${
                  isExported 
                    ? "bg-emerald-50 text-emerald-700" 
                    : isSelected 
                      ? "bg-signal/10" 
                      : "hover:bg-muted"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-base">{platform.icon}</span>
                  <div>
                    <span className="text-[14px] text-ink">{platform.label}</span>
                    <p className="text-[10px] text-steel">{platform.ratio}</p>
                  </div>
                </div>
                {isExported ? (
                  <Check className="h-4 w-4 text-emerald-600" />
                ) : (
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggle(platform.id)}
                    className="accent-signal"
                  />
                )}
              </label>
            );
          })}
        </div>

        {selected.length > 0 && (
          <button
            onClick={handleExport}
            disabled={exporting || !episode}
            className="mt-3 w-full rounded-md bg-ink px-3 py-2.5 text-[13px] text-white transition-colors hover:bg-[#1f2937] disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {exporting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Export to {selected.length} platform{selected.length > 1 ? "s" : ""}
              </>
            )}
          </button>
        )}

        {exportedPlatforms.length > 0 && !exporting && (
          <p className="mt-2 text-center text-xs text-steel">
            {allExported ? "All platforms exported!" : `${exportedPlatforms.length} exported`}
          </p>
        )}
      </PopoverContent>
    </Popover>
  );
}
