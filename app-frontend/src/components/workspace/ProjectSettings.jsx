import React, { useState } from "react";

const resolutions = ["720p", "1080p", "4K"];
const aspectRatios = ["16:9", "9:16", "1:1", "4:3"];
const frameRates = ["24 fps", "30 fps", "60 fps"];
const qualityPresets = ["Draft", "Standard", "High", "Ultra"];

export default function ProjectSettings() {
  const [projectName, setProjectName] = useState("20260803114305");
  const [resolution, setResolution] = useState("1080p");
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [frameRate, setFrameRate] = useState("30 fps");
  const [quality, setQuality] = useState("High");
  const [duration, setDuration] = useState(15);

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4 space-y-6">
      {/* Project name */}
      <div>
        <label className="text-xs text-white/40 uppercase tracking-wider mb-2 block">Project Name</label>
        <input
          type="text"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-[#dfff1e]/50"
        />
      </div>

      {/* Resolution */}
      <div>
        <label className="text-xs text-white/40 uppercase tracking-wider mb-2 block">Resolution</label>
        <div className="grid grid-cols-3 gap-2">
          {resolutions.map((r) => (
            <button
              key={r}
              onClick={() => setResolution(r)}
              className={`py-2 rounded-lg text-xs font-medium transition ${
                resolution === r
                  ? "bg-[#dfff1e] text-black"
                  : "bg-white/5 text-white/50 hover:text-white border border-white/10"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Aspect ratio */}
      <div>
        <label className="text-xs text-white/40 uppercase tracking-wider mb-2 block">Aspect Ratio</label>
        <div className="grid grid-cols-4 gap-2">
          {aspectRatios.map((ar) => (
            <button
              key={ar}
              onClick={() => setAspectRatio(ar)}
              className={`py-2 rounded-lg text-xs font-medium transition ${
                aspectRatio === ar
                  ? "bg-[#dfff1e] text-black"
                  : "bg-white/5 text-white/50 hover:text-white border border-white/10"
              }`}
            >
              {ar}
            </button>
          ))}
        </div>
      </div>

      {/* Frame rate */}
      <div>
        <label className="text-xs text-white/40 uppercase tracking-wider mb-2 block">Frame Rate</label>
        <div className="grid grid-cols-3 gap-2">
          {frameRates.map((fr) => (
            <button
              key={fr}
              onClick={() => setFrameRate(fr)}
              className={`py-2 rounded-lg text-xs font-medium transition ${
                frameRate === fr
                  ? "bg-[#dfff1e] text-black"
                  : "bg-white/5 text-white/50 hover:text-white border border-white/10"
              }`}
            >
              {fr}
            </button>
          ))}
        </div>
      </div>

      {/* Quality preset */}
      <div>
        <label className="text-xs text-white/40 uppercase tracking-wider mb-2 block">Quality</label>
        <div className="grid grid-cols-4 gap-2">
          {qualityPresets.map((q) => (
            <button
              key={q}
              onClick={() => setQuality(q)}
              className={`py-2 rounded-lg text-xs font-medium transition ${
                quality === q
                  ? "bg-[#dfff1e] text-black"
                  : "bg-white/5 text-white/50 hover:text-white border border-white/10"
              }`}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Duration slider */}
      <div>
        <label className="text-xs text-white/40 uppercase tracking-wider mb-2 block">
          Duration: <span className="text-white/70">{duration}s</span>
        </label>
        <input
          type="range"
          min="5"
          max="60"
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          className="w-full accent-[#dfff1e] cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-white/30 mt-1">
          <span>5s</span>
          <span>60s</span>
        </div>
      </div>

      {/* Save button */}
      <button className="w-full bg-[#dfff1e] text-black py-2.5 rounded-xl text-sm font-semibold hover:bg-[#c5e01a] transition">
        Save Settings
      </button>
    </div>
  );
}