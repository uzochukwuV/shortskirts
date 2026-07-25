import React from "react";
import { Link, useLocation } from "react-router-dom";
import { LayoutGrid, Film, Users, BarChart3, CalendarClock, Download, Settings, Plus } from "lucide-react";
import Button from "./Button";
import Breadcrumb from "./Breadcrumb";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutGrid },
  { label: "Series", path: "/dashboard", icon: Film },
  { label: "Characters", path: "/dashboard", icon: Users },
  { label: "Analytics", path: "/dashboard", icon: BarChart3 },
  { label: "Schedule", path: "/schedule", icon: CalendarClock },
  { label: "Exports", path: "/dashboard", icon: Download },
  { label: "Settings", path: "/settings", icon: Settings },
];

export default function AppChrome({ breadcrumb = [], actions, children }) {
  const location = useLocation();
  return (
    <div className="flex min-h-screen bg-paper">
      {/* Sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-mist md:flex">
        <div className="px-6 py-5">
          <Link to="/" className="font-display text-[20px] font-medium tracking-tight-bold text-ink">
            Dysentry
          </Link>
        </div>
        <div className="px-3">
          <Link to="/dashboard">
            <Button className="w-full justify-start px-4 py-2.5 text-[14px]">
              <Plus className="h-4 w-4" /> New series
            </Button>
          </Link>
        </div>
        <nav className="mt-6 flex-1 px-3">
          {navItems.map((item) => {
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.label}
                to={item.path}
                className={`mb-1 flex items-center gap-3 rounded-lg px-4 py-2.5 text-[14px] transition-colors ${active ? "font-medium text-ink" : "text-steel hover:text-ink"}`}
              >
                <item.icon className="h-4 w-4" /> {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-mist px-3 py-4">
          <Link to="/settings" className={`flex items-center gap-3 rounded-lg px-4 py-2.5 text-[14px] transition-colors ${location.pathname === "/settings" ? "font-medium text-ink" : "text-steel hover:text-ink"}`}>
            <Settings className="h-4 w-4" /> Settings
          </Link>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col">
        <header className="flex items-center gap-4 border-b border-mist px-6 py-4">
          <Breadcrumb items={breadcrumb} />
          <div className="ml-auto flex items-center gap-3">{actions}</div>
        </header>
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}