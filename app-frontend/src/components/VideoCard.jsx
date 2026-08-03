import React from 'react';
import { Play } from 'lucide-react';

export default function VideoCard({ title, author, image_url, description }) {
  return (
    <div className="group relative rounded-2xl overflow-hidden bg-[#141414] border border-white/5 cursor-pointer transition-all duration-300 hover:border-white/20 hover:scale-[1.02]">
      <div className="aspect-[4/3] overflow-hidden relative">
        <img
          src={image_url}
          alt={title}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />

        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="w-12 h-12 rounded-full bg-[#e0ff4c]/90 flex items-center justify-center backdrop-blur-sm">
            <Play size={18} className="text-black ml-0.5" fill="black" />
          </div>
        </div>

        {description && (
          <div className="absolute top-3 left-3 right-3">
            <span className="text-xs text-white/60 uppercase tracking-wider">{description}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between px-3 py-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
            <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
              <circle cx="6" cy="4" r="2.2" stroke="white" strokeWidth="1" opacity="0.6" />
              <path d="M2 10C2 8 4 7 6 7C8 7 10 8 10 10" stroke="white" strokeWidth="1" opacity="0.6" strokeLinecap="round" />
            </svg>
          </div>
          <span className="text-sm text-white truncate font-medium">{title}</span>
        </div>
        <span className="text-xs text-white/40 flex-shrink-0 ml-2">{author}</span>
      </div>
    </div>
  );
}
