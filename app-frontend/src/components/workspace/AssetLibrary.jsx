import React from "react";
import { Upload, Film, Image, Music, Plus } from "lucide-react";

const assets = [
  { name: "Desert Storm.mp4", type: "video", duration: "0:15", icon: Film },
  { name: "City Skyline.mp4", type: "video", duration: "0:08", icon: Film },
  { name: "Desert Wide.png", type: "image", duration: "—", icon: Image },
  { name: "Character Ref.png", type: "image", duration: "—", icon: Image },
  { name: "Storm Audio.mp3", type: "audio", duration: "0:15", icon: Music },
  { name: "Ambient.mp3", type: "audio", duration: "0:30", icon: Music },
  { name: "Final Render.mp4", type: "video", duration: "0:15", icon: Film },
  { name: "Logo Overlay.png", type: "image", duration: "—", icon: Image },
];

const typeColors = {
  video: "text-[#dfff1e] bg-[#dfff1e]/10",
  image: "text-blue-400 bg-blue-400/10",
  audio: "text-purple-400 bg-purple-400/10",
};

export default function AssetLibrary() {
  return (
    <div className="flex flex-col h-full">
      {/* Upload bar */}
      <div className="flex items-center gap-2 p-4 border-b border-white/10 flex-shrink-0">
        <button className="flex items-center gap-1.5 bg-[#dfff1e] text-black text-xs font-medium px-3 py-1.5 rounded-full hover:bg-[#c5e01a] transition">
          <Upload size={14} /> Upload
        </button>
        <button className="flex items-center gap-1.5 text-white/40 text-xs px-3 py-1.5 rounded-full border border-white/10 hover:text-white/70 hover:bg-white/5 transition">
          <Plus size={14} /> New folder
        </button>
      </div>

      {/* Asset grid */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-2 gap-3">
          {assets.map((asset) => {
            const Icon = asset.icon;
            return (
              <div
                key={asset.name}
                className="bg-white/5 border border-white/10 rounded-xl p-3 hover:border-[#dfff1e]/30 cursor-pointer transition group"
              >
                <div className={`w-full aspect-video rounded-lg flex items-center justify-center mb-2 ${typeColors[asset.type]}`}>
                  <Icon size={20} />
                </div>
                <p className="text-xs text-white/70 truncate">{asset.name}</p>
                <p className="text-[10px] text-white/30 mt-0.5">{asset.duration}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}