import React, { useState } from "react";
import { Plus, ChevronDown, Send } from "lucide-react";

export default function AIToolsPanel() {
  const [message, setMessage] = useState("");

  return (
    <div className="flex flex-col h-full">
      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="text-sm text-white/70 leading-relaxed">
          A lone figure marches across a storm-filled desert, their silhouette framed by lightning
          strikes that illuminate towering dunes. The sky churns with dark clouds, casting dramatic
          shadows across the endless sand...
        </div>
        <div className="text-sm text-white/50">
          I'll create a 15-second, 16:9 cinematic fantasy action clip featuring this desert storm
          sequence.
        </div>
        <div className="bg-white/5 rounded-lg p-3 text-xs text-white/40 border border-white/5">
          The task has been canceled.
        </div>

        {/* Pro features card */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
          <p className="text-sm text-white font-medium mb-1">You're using Pro features</p>
          <p className="text-xs text-white/40 mb-3">Upgrade to Pro to keep using them...</p>
          <div className="flex gap-2">
            <button className="text-xs text-white/60 px-3 py-1.5 rounded-full border border-white/10 hover:bg-white/5 transition">
              Continue
            </button>
            <button className="text-xs bg-[#dfff1e] text-black font-medium px-3 py-1.5 rounded-full hover:bg-[#c5e01a] transition">
              Upgrade
            </button>
          </div>
        </div>
      </div>

      {/* Input footer */}
      <div className="border-t border-white/10 p-3 flex-shrink-0">
        <div className="bg-white/5 rounded-xl border border-white/10 p-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Enter ideas, scenes, or screenplay..."
            rows={2}
            className="w-full bg-transparent text-white text-sm placeholder:text-white/30 focus:outline-none resize-none"
          />
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <button className="text-white/40 hover:text-white transition">
              <Plus size={16} />
            </button>
            <button className="text-white/40 text-xs flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/5 hover:text-white/70 transition">
              Auto <ChevronDown size={10} />
            </button>
            <button className="text-white/40 text-xs px-2 py-0.5 rounded-full bg-white/5 hover:text-white/70 transition">
              Skills
            </button>
            <button className="ml-auto w-8 h-8 rounded-full bg-[#dfff1e] flex items-center justify-center text-black hover:bg-[#c5e01a] transition flex-shrink-0">
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}