import React from "react";
import { Link } from "react-router-dom";

export default function Navbar({ onStartClick }) {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#0a0a0a]/80 backdrop-blur-xl border-b border-white/5">
      <nav className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-10 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <span className="text-lg sm:text-xl font-extrabold tracking-tighter text-white" style={{ fontFamily: 'ui-sans-serif, system-ui, sans-serif' }}>
            SONICVISION
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          <button className="text-white/80 hover:text-white text-sm font-medium flex items-center gap-1 transition-colors">
            Models
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="opacity-60">
              <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button className="text-white/80 hover:text-white text-sm font-medium flex items-center gap-1 transition-colors">
            Skills
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="opacity-60">
              <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button className="text-white/80 hover:text-white text-sm font-medium transition-colors">
            Blogs
          </button>
        </div>

        <button onClick={onStartClick} className="bg-[#e0ff4c] text-black text-xs sm:text-sm font-semibold px-4 sm:px-5 py-2 rounded-full hover:bg-[#d4f53e] transition-colors flex-shrink-0">
          Start for free
        </button>
      </nav>
    </header>
  );
}