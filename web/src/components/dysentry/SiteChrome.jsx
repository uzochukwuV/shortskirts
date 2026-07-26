import React from "react";
import { Link } from "react-router-dom";
import { Search, ArrowRight } from "lucide-react";
import Button from "./Button";

const navLinks = ["Features", "Pipeline", "Analytics", "Pricing"];

const footerCols = [
  { title: "Product", links: ["Features", "Pipeline", "Analytics", "Publishing", "Pricing"] },
  { title: "Company", links: ["About", "Careers", "Blog", "Contact"] },
  { title: "Resources", links: ["Documentation", "Guides", "Changelog", "Status"] },
  { title: "Legal", links: ["Privacy", "Terms", "Security"] },
];

export default function SiteChrome({ children }) {
  return (
    <div className="min-h-screen bg-paper">
      {/* Announcement bar */}
      <div className="w-full bg-ink text-white">
        <div className="mx-auto max-w-[1280px] px-6 py-2 text-center text-[14px]" style={{ lineHeight: 1.5 }}>
          New — Auto-publishing now supports TikTok and Reels.{" "}
          <span className="cursor-pointer underline underline-offset-2">Read the changelog</span>
        </div>
      </div>

      {/* Navbar */}
      <header className="border-b border-mist">
        <nav className="mx-auto flex max-w-[1280px] items-center gap-8 px-6 py-4">
          <Link to="/" className="font-display text-[20px] font-medium tracking-tight-bold text-ink">
            Dysentry
          </Link>
          <div className="ml-4 hidden items-center gap-6 lg:flex">
            {navLinks.map((item) => (
              <span key={item} className="cursor-pointer text-[16px] text-ink transition-colors hover:text-steel">
                {item}
              </span>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-4">
            <div className="hidden items-center gap-2 rounded-lg border border-mist px-3 py-2 md:flex">
              <Search className="h-4 w-4 text-steel" />
              <input
                placeholder="Search"
                className="w-28 bg-transparent text-[14px] text-ink outline-none placeholder-steel"
              />
            </div>
            <Link to="/login" className="hidden text-[16px] text-ink transition-colors hover:text-steel sm:inline">
              Sign in
            </Link>
            <Link to="/register">
              <Button className="px-5 py-2.5 text-[14px]">
                Start creating <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </nav>
      </header>

      <main>{children}</main>

      {/* Footer */}
      <footer className="mt-[104px] bg-ink text-white">
        <div className="mx-auto max-w-[1280px] px-6 py-16">
          <div className="grid gap-12 md:grid-cols-[1.5fr_1fr_1fr_1fr_1fr]">
            <div>
              <p className="font-display text-[20px] font-medium tracking-tight-bold">Dysentry</p>
              <p className="mt-3 max-w-xs text-[14px] text-white/60" style={{ lineHeight: 1.5 }}>
                Serialized short-form stories with consistent characters, approval checkpoints, and automated publishing.
              </p>
            </div>
            {footerCols.map((col) => (
              <div key={col.title}>
                <p className="text-[11px] font-medium tracking-tight-bold text-white/40 uppercase">{col.title}</p>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l}>
                      <span className="cursor-pointer text-[14px] text-white/80 transition-colors hover:text-white">{l}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-white/10 pt-8 text-[13px] text-white/50 sm:flex-row">
            <p>© 2026 Dysentry. All rights reserved.</p>
            <p>Made for creators and brands.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}