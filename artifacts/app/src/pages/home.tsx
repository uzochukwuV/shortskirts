import { motion } from "framer-motion";
import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Layout } from "@/components/layout";
import {
  ArrowRight, CheckCircle2, Cpu, Film, Layers,
  Users, Briefcase, BookOpen, Gamepad2, TrendingUp,
  LayoutTemplate, ChevronRight, Play,
} from "lucide-react";

// ─── Templates data ───────────────────────────────────────────────────────────

const TEMPLATES = [
  { icon: "📢", label: "Product Launch Ad",    sub: "15/30/60s video concepts from brief",   tag: "Brand" },
  { icon: "🎌", label: "Anime Trailer",          sub: "Cinematic series teaser with characters", tag: "Creator" },
  { icon: "📱", label: "TikTok Serial Episode",  sub: "Vertical short-form serialized story",  tag: "Social" },
  { icon: "🎓", label: "Course Lesson",          sub: "Animated explainer with narrator char",  tag: "Education" },
  { icon: "⚔️", label: "Game Lore Short",        sub: "Cinematic world-building & lore reveal", tag: "Web3 / Game" },
  { icon: "👤", label: "Character Reveal",       sub: "Introduce your mascot or protagonist",   tag: "Creator" },
];

// ─── ICP rows ─────────────────────────────────────────────────────────────────

const ICPS = [
  {
    icon: <Users className="h-5 w-5" />,
    who: "Indie Creators",
    tagline: "Build a serialized world — not a one-off clip",
    detail: "Define your cast once. Every episode remembers them. Regenerate any scene without rebuilding the whole pipeline.",
    color: "bg-violet-50 text-violet-600",
  },
  {
    icon: <Briefcase className="h-5 w-5" />,
    who: "Agencies",
    tagline: "Produce ad campaigns for dozens of clients",
    detail: "Each client gets their own brand bible. Approve the storyboard before a single frame renders. Ship polished 15/30/60s cuts.",
    color: "bg-blue-50 text-blue-600",
  },
  {
    icon: <TrendingUp className="h-5 w-5" />,
    who: "Small Businesses",
    tagline: "Social video at agency quality, not agency cost",
    detail: "Start with a template. Drop in your product brief. Get vertical video, captions, and post copy — ready to schedule.",
    color: "bg-emerald-50 text-emerald-600",
  },
  {
    icon: <BookOpen className="h-5 w-5" />,
    who: "Educators",
    tagline: "Animated explainers from your course content",
    detail: "Paste your lesson notes. Characters and storyboard are auto-generated. Edit individual scenes before final render.",
    color: "bg-amber-50 text-amber-600",
  },
  {
    icon: <Gamepad2 className="h-5 w-5" />,
    who: "Web3 & Game Teams",
    tagline: "IP bible → trailers, lore videos, character teasers",
    detail: "Cinematic shorts for your universe. Consistent character designs across every piece of content.",
    color: "bg-rose-50 text-rose-600",
  },
];

// ─── How it works ─────────────────────────────────────────────────────────────

const HOW = [
  { n: "01", title: "Choose a workflow",   desc: "Pick from templates: Brand Campaign, Creator Series, Explainer, Social Short, Game Lore." },
  { n: "02", title: "Write the brief",     desc: "Paste your prompt or product brief. Qwen generates a full episode plan with characters and scene breakdowns." },
  { n: "03", title: "Approve the outline", desc: "Review the plan before anything renders. Edit scenes, swap characters, tweak tone. Approve when ready." },
  { n: "04", title: "Generate & iterate",  desc: "Wan 2.7 renders each scene. Regenerate individual scenes without rerunning the whole pipeline." },
  { n: "05", title: "Export & publish",    desc: "Download the assembled episode, captions, post copy, and platform-specific cuts." },
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function Home() {
  return (
    <Layout>
      <div className="flex-1 bg-white">

        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="relative overflow-hidden bg-white pt-20">
          <div className="absolute inset-0 bg-gradient-to-b from-violet-50/60 via-white to-white pointer-events-none" />
          <div className="container px-4 md:px-6 relative">
            <div className="max-w-3xl mx-auto text-center pt-10 pb-16">
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
              >
                <div className="inline-flex items-center gap-2 text-xs font-medium text-violet-700 bg-violet-50 border border-violet-200 rounded-full px-3 py-1 mb-6">
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-500" />
                  AI Showrunner for branded video series
                </div>

                <h1 className="text-5xl md:text-6xl font-bold tracking-tight text-gray-900 mb-4 leading-[1.1]">
                  Consistent characters.{" "}
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-600 to-fuchsia-500">
                    Repeatable production.
                  </span>
                </h1>

                <p className="text-xl text-gray-500 max-w-xl mx-auto mb-8 leading-relaxed">
                  Create a brief, approve the storyboard, generate each scene — and regenerate any single
                  scene without rerunning the whole pipeline. Built for creators and teams who ship video weekly.
                </p>

                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <Link href="/dashboard">
                    <Button size="lg" className="bg-gray-900 hover:bg-gray-700 text-white font-medium px-7 h-11 rounded-xl text-sm">
                      Start for free <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                  <Link href="/pricing">
                    <Button size="lg" variant="outline" className="border-gray-200 text-gray-700 hover:bg-gray-50 font-medium px-7 h-11 rounded-xl text-sm">
                      See pricing
                    </Button>
                  </Link>
                </div>
              </motion.div>
            </div>
          </div>

          {/* Aurora strip */}
          <div className="w-full overflow-hidden h-40 relative">
            <div className="absolute inset-0 bg-gradient-to-r from-violet-200/40 via-fuchsia-200/30 to-blue-200/40 blur-2xl scale-110" />
            {/* Template preview cards floating */}
            <div className="absolute inset-0 flex items-center justify-center gap-3 px-4 overflow-hidden">
              {TEMPLATES.map((t, i) => (
                <motion.div
                  key={t.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.07, duration: 0.4 }}
                  className="bg-white/90 border border-gray-200 rounded-xl px-3 py-2 shadow-sm shrink-0 hidden sm:flex items-center gap-2"
                >
                  <span className="text-lg">{t.icon}</span>
                  <span className="text-xs font-medium text-gray-700 whitespace-nowrap">{t.label}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Who it's for ─────────────────────────────────────────────── */}
        <section className="py-20 bg-white">
          <div className="container px-4 md:px-6">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                Built for teams that{" "}
                <span className="text-violet-600">ship video weekly</span>
              </h2>
              <p className="text-gray-500 max-w-lg mx-auto">
                Not a one-click AI toy. A production system for the workflows that actually make money.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
              {ICPS.map((icp) => (
                <div
                  key={icp.who}
                  className="bg-white border border-gray-200 rounded-2xl p-6 hover:border-violet-300 hover:shadow-sm transition-all group"
                >
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-4 ${icp.color}`}>
                    {icp.icon}
                  </div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">{icp.who}</div>
                  <h3 className="font-semibold text-gray-900 mb-2 leading-snug">{icp.tagline}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{icp.detail}</p>
                </div>
              ))}

              {/* CTA card */}
              <div className="bg-gradient-to-br from-violet-600 to-fuchsia-600 rounded-2xl p-6 flex flex-col justify-between">
                <div>
                  <LayoutTemplate className="h-6 w-6 text-white/80 mb-4" />
                  <h3 className="font-semibold text-white mb-2 leading-snug">Start with a template</h3>
                  <p className="text-sm text-white/70 leading-relaxed">
                    10+ pre-built workflows with structure, scene count, pacing, and output format already configured.
                  </p>
                </div>
                <Link href="/dashboard">
                  <button className="mt-6 flex items-center gap-2 text-sm font-medium text-white hover:gap-3 transition-all">
                    Browse templates <ChevronRight className="h-4 w-4" />
                  </button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* ── How it works ─────────────────────────────────────────────── */}
        <section className="py-20 bg-gray-50 border-y border-gray-100">
          <div className="container px-4 md:px-6">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                How StoryForge works
              </h2>
              <p className="text-gray-500 max-w-md mx-auto">
                Controlled autonomy — not a black box. You approve every stage before it costs you a render.
              </p>
            </div>

            <div className="max-w-2xl mx-auto space-y-0">
              {HOW.map((step, i) => (
                <div key={step.n} className="flex gap-5">
                  {/* Connector */}
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-violet-600 text-white text-xs font-bold flex items-center justify-center shrink-0">
                      {i + 1}
                    </div>
                    {i < HOW.length - 1 && <div className="w-px flex-1 bg-violet-200 my-1" />}
                  </div>
                  {/* Content */}
                  <div className="pb-8">
                    <div className="text-[10px] font-mono text-gray-400 mb-0.5">{step.n}</div>
                    <h3 className="font-semibold text-gray-900 mb-1">{step.title}</h3>
                    <p className="text-sm text-gray-500 leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Key capabilities ──────────────────────────────────────────── */}
        <section className="py-20 bg-white">
          <div className="container px-4 md:px-6">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-3">
                The orchestration layer{" "}
                <span className="text-violet-600">that sets us apart</span>
              </h2>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {[
                {
                  icon: <Layers className="h-5 w-5" />,
                  title: "Character & Brand Memory",
                  desc: "Define characters once. Their appearance, personality, and voice persist across every episode, every campaign, every scene — stored in CockroachDB.",
                  items: ["Character bibles", "Brand bibles", "Visual consistency"],
                },
                {
                  icon: <Film className="h-5 w-5" />,
                  title: "Granular Regeneration",
                  desc: "Regenerate one scene, one character ref, or one intro — without rerunning the whole pipeline. Every stage is independently addressable.",
                  items: ["Per-scene regeneration", "Character ref swap", "Aspect ratio variants"],
                },
                {
                  icon: <Cpu className="h-5 w-5" />,
                  title: "Approval Gates",
                  desc: "Approve the outline before video renders. Approve character refs before scene generation. No wasted renders on content you wouldn't publish.",
                  items: ["Outline approval", "Character approval", "Scene-level review"],
                },
              ].map(c => (
                <div key={c.title} className="bg-white border border-gray-200 rounded-2xl p-6 hover:border-violet-300 hover:shadow-sm transition-all">
                  <div className="w-9 h-9 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center mb-4">
                    {c.icon}
                  </div>
                  <h3 className="font-semibold text-gray-900 mb-2">{c.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed mb-4">{c.desc}</p>
                  <ul className="space-y-1.5">
                    {c.items.map(item => (
                      <li key={item} className="flex items-center gap-2 text-xs text-gray-600">
                        <CheckCircle2 className="h-3.5 w-3.5 text-violet-500 shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Template gallery ──────────────────────────────────────────── */}
        <section className="py-20 bg-gray-50 border-t border-gray-100">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-10 gap-4">
              <div>
                <h2 className="text-3xl font-bold text-gray-900 mb-2">Production templates</h2>
                <p className="text-gray-500">Start fast with structure already configured.</p>
              </div>
              <Link href="/dashboard">
                <Button variant="outline" size="sm" className="border-gray-200 text-gray-600 rounded-lg text-sm">
                  Use a template <ArrowRight className="ml-2 h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {TEMPLATES.map(t => (
                <Link key={t.label} href="/dashboard">
                  <div className="bg-white border border-gray-200 hover:border-violet-300 hover:shadow-sm rounded-2xl p-5 cursor-pointer transition-all group">
                    <span className="text-2xl mb-3 block">{t.icon}</span>
                    <div className="text-[10px] font-semibold uppercase tracking-widest text-violet-500 mb-1">{t.tag}</div>
                    <h3 className="font-semibold text-gray-900 text-sm mb-1 group-hover:text-violet-600 transition-colors">{t.label}</h3>
                    <p className="text-xs text-gray-400 leading-relaxed">{t.sub}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* ── Stats ────────────────────────────────────────────────────── */}
        <section className="py-16 bg-white border-y border-gray-100">
          <div className="container px-4 md:px-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              {[
                { value: "Qwen-Plus",  label: "Story & Script" },
                { value: "Wan 2.7",    label: "Video Render" },
                { value: "B2 + CRDB",  label: "Storage & Memory" },
                { value: "< 10 min",   label: "Per Episode" },
              ].map(s => (
                <div key={s.label}>
                  <div className="flex items-center justify-center gap-2 mb-1">
                    <span className="w-2 h-2 rounded-full bg-violet-500" />
                    <span className="text-xl font-bold text-gray-900">{s.value}</span>
                  </div>
                  <span className="text-xs text-gray-400 uppercase tracking-wider">{s.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CTA ──────────────────────────────────────────────────────── */}
        <section className="py-24 bg-gray-900">
          <div className="container px-4 md:px-6 text-center">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Your characters. Your series. On autopilot.
            </h2>
            <p className="text-gray-400 max-w-md mx-auto mb-8">
              Join creators and agencies using StoryForge to ship branded video series every week.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link href="/dashboard">
                <Button size="lg" className="bg-white hover:bg-gray-100 text-gray-900 font-medium px-8 h-12 rounded-xl">
                  Start free <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/pricing">
                <Button size="lg" variant="outline" className="border-gray-700 text-gray-300 hover:bg-gray-800 font-medium px-8 h-12 rounded-xl">
                  View pricing
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}
