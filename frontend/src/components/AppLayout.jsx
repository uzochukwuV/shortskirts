import React from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Home,
  Clapperboard,
  Library,
  Film,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Logo from "@/components/Logo";

const NAV = [
  { label: "Home", path: "/", icon: Home },
  { label: "Studio", path: "/studio", icon: Clapperboard },
  { label: "Library", path: "/library", icon: Library },
  { label: "Reels", path: "/reels", icon: Film },
  { label: "Profile", path: "/profile", icon: User },
];

export default function AppLayout({ children }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-canvas">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-border bg-card/60 glass lg:flex">
        <div className="flex h-16 items-center px-6">
          <Logo />
        </div>
        <nav className="flex-1 space-y-1 px-3 py-2">
          {NAV.map((item) => {
            const active = item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all",
                  active
                    ? "bg-ink text-white shadow-sm"
                    : "text-muted-foreground hover:bg-accent hover:text-ink"
                )}
              >
                <Icon className="h-[18px] w-[18px]" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4">
          <Link
            to="/studio"
            className="flex items-center justify-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-transform hover:scale-[1.02]"
          >
            <Clapperboard className="h-4 w-4" />
            New video
          </Link>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-card/80 px-4 glass lg:hidden">
        <Logo />
        <Link
          to="/studio"
          className="inline-flex h-9 items-center gap-1.5 rounded-full bg-ink px-3.5 text-xs font-semibold text-white"
        >
          <Clapperboard className="h-3.5 w-3.5" />
          Create
        </Link>
      </header>

      {/* Main content */}
      <main className="lg:pl-64">
        <div className="mx-auto w-full max-w-6xl px-4 pb-28 pt-6 sm:px-6 lg:pb-12 lg:pt-10">
          {children}
        </div>
      </main>

      {/* Mobile bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/85 glass lg:hidden">
        <div className="mx-auto flex max-w-md items-stretch justify-around px-2 pb-[env(safe-area-inset-bottom)]">
          {NAV.map((item) => {
            const active = item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors",
                  active ? "text-ink" : "text-muted-foreground"
                )}
              >
                <Icon className={cn("h-5 w-5", active && "scale-110")} strokeWidth={active ? 2.4 : 1.8} />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}