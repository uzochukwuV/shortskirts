const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Film, Heart, Sparkles, Crown, ChevronRight, Settings, Bell, Shield, HelpCircle, LogOut, ArrowUpRight } from "lucide-react";
import AppLayout from "@/components/AppLayout";

const MENU = [
  { icon: Settings, label: "Account settings", desc: "Manage your preferences" },
  { icon: Bell, label: "Notifications", desc: "Push & email alerts" },
  { icon: Shield, label: "Privacy & security", desc: "Control your data" },
  { icon: HelpCircle, label: "Help & support", desc: "FAQs and contact" },
];

export default function Profile() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({ videos: 0, likes: 0 });

  useEffect(() => {
    db.auth.me().then(setUser).catch(() => {});
    db.entities.Video.list("-created_date", 200).then((data) => {
      const v = data || [];
      setStats({ videos: v.length, likes: v.reduce((a, b) => a + (b.likes || 0), 0) });
    });
  }, []);

  const signOut = async () => {
    await db.auth.logout();
  };

  const initial = (user?.full_name || user?.email || "V")[0]?.toUpperCase();

  return (
    <AppLayout>
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-ink text-2xl font-bold text-white sm:h-20 sm:w-20">
            {initial}
          </div>
          <div>
            <h1 className="font-display text-xl font-bold tracking-tight sm:text-2xl">{user?.full_name || "Creator"}</h1>
            <p className="text-sm text-muted-foreground">{user?.email || "Welcome to Vivomatica"}</p>
            <span className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-ink/5 px-2.5 py-0.5 text-[11px] font-medium text-ink">
              <Crown className="h-3 w-3" /> Creator plan
            </span>
          </div>
        </div>
      </motion.div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        {[
          { icon: Film, label: "Videos", value: stats.videos },
          { icon: Heart, label: "Likes", value: stats.likes },
          { icon: Sparkles, label: "Credits", value: 128 },
        ].map((s) => {
          const Icon = s.icon;
          return (
            <div key={s.label} className="rounded-2xl border border-border bg-card p-4 text-center shadow-sm">
              <Icon className="mx-auto h-4 w-4 text-ink" />
              <p className="mt-1.5 font-display text-xl font-bold">{s.value}</p>
              <p className="text-[11px] text-muted-foreground">{s.label}</p>
            </div>
          );
        })}
      </div>

      {/* Subscription banner */}
      <Link to="/plans" className="mb-6 flex items-center justify-between rounded-2xl bg-ink p-5 text-white transition-transform hover:scale-[1.01]">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10"><Crown className="h-5 w-5" /></span>
          <div>
            <p className="text-sm font-semibold">Upgrade to Studio</p>
            <p className="text-xs text-white/70">4K exports · team seats · priority rendering</p>
          </div>
        </div>
        <ArrowUpRight className="h-5 w-5" />
      </Link>

      {/* Settings menu */}
      <div className="grid gap-3 sm:grid-cols-2">
        {MENU.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.label} className="flex items-center gap-3 rounded-2xl border border-border bg-card p-4 text-left shadow-sm transition-colors hover:border-ink/30">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary text-ink"><Icon className="h-4 w-4" /></span>
              <div className="flex-1">
                <p className="text-sm font-medium">{item.label}</p>
                <p className="text-xs text-muted-foreground">{item.desc}</p>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </button>
          );
        })}
      </div>

      {/* Sign out */}
      <button onClick={signOut} className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-border bg-card py-3.5 text-sm font-semibold text-destructive shadow-sm hover:bg-destructive/5">
        <LogOut className="h-4 w-4" /> Sign out
      </button>

      <p className="mt-6 text-center text-[11px] text-muted-foreground">Vivomatica AI · v1.0.0</p>
    </AppLayout>
  );
}