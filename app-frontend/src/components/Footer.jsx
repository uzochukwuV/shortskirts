import React from "react";

export default function Footer() {
  return (
    <footer className="border-t border-white/5 bg-[#0a0a0a]">
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="col-span-2 md:col-span-1">
            <span className="text-xl font-extrabold tracking-tighter text-white">SONICVISION</span>
            <p className="text-sm text-white/40 mt-3 max-w-[200px]">
              Pro Video, Made Easy. Create stunning AI-powered videos in minutes.
            </p>
          </div>

          {[
            { title: "Product", links: ["Nano Pro", "Seedance 2", "GPT Image 2", "Pricing"] },
            { title: "Resources", links: ["Models", "Skills", "Blogs", "API Docs"] },
            { title: "Company", links: ["About", "Careers", "Contact", "Terms"] },
          ].map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-white/80 mb-3">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map((link) => (
                  <li key={link}>
                    <a href="#" className="text-sm text-white/40 hover:text-[#e0ff4c] transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-8 border-t border-white/5">
          <p className="text-xs text-white/30">© 2026 SonicVision. All rights reserved.</p>
          <div className="flex gap-4">
            {["Twitter", "YouTube", "Discord", "Instagram"].map((social) => (
              <a key={social} href="#" className="text-xs text-white/30 hover:text-[#e0ff4c] transition-colors">
                {social}
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* Floating chat button */}
      <button className="fixed bottom-6 right-6 w-12 h-12 rounded-full bg-[#e0ff4c] flex items-center justify-center shadow-lg hover:scale-110 transition-transform z-50">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M12 3C6.5 3 2 6.5 2 11C2 13 3 14.8 4.5 16L4 19L7.5 17.5C9 18 10.5 18.3 12 18.3C17.5 18.3 22 14.8 22 10.5C22 6.2 17.5 3 12 3Z" fill="black" />
        </svg>
      </button>
    </footer>
  );
}