import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Sparkles,
  Wand2,
  MessageSquareText,
  Share2,
  Play,
  Star,
  Check,
} from "lucide-react";
import Logo from "@/components/Logo";

const FEATURES = [
  {
    icon: Wand2,
    title: "Prompt to cinematic",
    desc: "Describe a scene in plain language and Vivomatica renders a high-fidelity video in seconds.",
  },
  {
    icon: MessageSquareText,
    title: "Chat to edit",
    desc: "Refine your creation through conversation — \"make it slower\", \"add golden light\" — and it re-renders.",
  },
  {
    icon: Share2,
    title: "Direct to social",
    desc: "Export straight to TikTok, Instagram, and YouTube with captions written for you.",
  },
];

const TESTIMONIALS = [
  { name: "Mara V.", role: "Content Creator", text: "I shipped a week of reels in an afternoon. The chat-to-edit flow is magic." },
  { name: "Devin K.", role: "Brand Director", text: "Cinematic quality without a crew. Our product launches have never looked better." },
  { name: "Aïsha L.", role: "Indie Filmmaker", text: "It feels like having a DP in my pocket. The motion styles are genuinely filmic." },
];

const PLANS = [
  { name: "Starter", price: "$0", tagline: "For trying things out", features: ["10 renders / mo", "720p exports", "Watermark"] },
  { name: "Creator", price: "$24", tagline: "For serious creators", features: ["Unlimited renders", "1080p exports", "No watermark", "Chat-to-edit"], featured: true },
  { name: "Studio", price: "$79", tagline: "For teams & brands", features: ["4K exports", "Brand presets", "Priority rendering", "Team seats"] },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-border glass">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Logo />
          <nav className="hidden items-center gap-7 text-sm text-muted-foreground md:flex">
            <a href="#features" className="hover:text-ink">Features</a>
            <a href="#showcase" className="hover:text-ink">Showcase</a>
            <a href="#pricing" className="hover:text-ink">Pricing</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/onboarding" className="hidden text-sm font-medium text-muted-foreground hover:text-ink sm:block">Sign in</Link>
            <Link to="/onboarding" className="inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white">
              Get started <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="mx-auto max-w-6xl px-5 pb-16 pt-16 sm:pt-24">
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
                <Sparkles className="h-3.5 w-3.5" /> AI video production, reimagined
              </span>
              <h1 className="mt-5 font-display text-4xl font-extrabold leading-[1.05] tracking-tight text-balance sm:text-5xl lg:text-6xl">
                Cinematic video,<br />from a single sentence.
              </h1>
              <p className="mt-5 max-w-md text-base text-muted-foreground sm:text-lg">
                Vivomatica AI turns your words into film-grade video. Create, refine through chat, and publish to every platform — all from your phone.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Link to="/onboarding" className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-ink/10 transition-transform hover:scale-[1.02]">
                  Start creating <ArrowRight className="h-4 w-4" />
                </Link>
                <a href="#showcase" className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-6 py-3 text-sm font-semibold text-ink hover:border-ink/40">
                  <Play className="h-4 w-4 fill-ink" /> Watch showcase
                </a>
              </div>
              <div className="mt-8 flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  {Array.from({ length: 5 }).map((_, i) => <Star key={i} className="h-3.5 w-3.5 fill-ink text-ink" />)}
                </span>
                Loved by 40,000+ creators
              </div>
            </motion.div>

            {/* Visual */}
            <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.1 }} className="relative">
              <div className="relative mx-auto max-w-md">
                <div className="overflow-hidden rounded-3xl border border-border bg-card shadow-2xl shadow-ink/10">
                  <div className="relative aspect-[4/5]">
                    <img src="https://images.unsplash.com/photo-1518709268805-4e9042af2176?w=800&q=80" alt="" className="h-full w-full object-cover" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
                    <div className="absolute bottom-0 left-0 right-0 p-5 text-white">
                      <p className="text-xs text-white/70">Prompt</p>
                      <p className="mt-1 text-sm font-medium">A neon-lit Tokyo street in the rain at midnight</p>
                      <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-white/90 px-3 py-1.5 text-xs font-semibold text-ink">
                        <Sparkles className="h-3.5 w-3.5" /> Rendering…
                      </div>
                    </div>
                  </div>
                </div>
                <div className="absolute -left-6 -top-6 hidden rounded-2xl border border-border bg-card p-3 shadow-xl sm:block animate-float">
                  <div className="flex items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-white"><MessageSquareText className="h-4 w-4" /></span>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Chat edit</p>
                      <p className="text-xs font-semibold">"Add golden light"</p>
                    </div>
                  </div>
                </div>
                <div className="absolute -bottom-5 -right-3 hidden rounded-2xl border border-border bg-card p-3 shadow-xl sm:block animate-float" style={{ animationDelay: "1.5s" }}>
                  <div className="flex items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-white"><Share2 className="h-4 w-4" /></span>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Published to</p>
                      <p className="text-xs font-semibold">TikTok · Instagram</p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t border-border bg-card/50">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:py-24">
          <div className="max-w-2xl">
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">Everything you need to make video.</h2>
            <p className="mt-3 text-muted-foreground">From the first idea to the final post — one fluid workflow, built for mobile.</p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div key={f.title} className="rounded-2xl border border-border bg-card p-6 transition-shadow hover:shadow-lg hover:shadow-ink/5">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-ink text-white">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-4 text-base font-semibold">{f.title}</h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Showcase */}
      <section id="showcase" className="border-t border-border">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:py-24">
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">Made with Vivomatica.</h2>
          <p className="mt-3 text-muted-foreground">A glimpse of what creators are shipping right now.</p>
          <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {[
              "https://images.unsplash.com/photo-1542051841857-5f90071e7989?w=600&q=80",
              "https://images.unsplash.com/photo-1614728263952-84ea256f9679?w=600&q=80",
              "https://images.unsplash.com/photo-1506784983877-45594efa4cbe?w=600&q=80",
              "https://images.unsplash.com/photo-1485462537746-965f33f7f6a7?w=600&q=80",
              "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=600&q=80",
              "https://images.unsplash.com/photo-1557672172-298e090bd0f1?w=600&q=80",
              "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=600&q=80",
              "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=600&q=80",
            ].map((src, i) => (
              <div key={i} className="group relative aspect-square overflow-hidden rounded-2xl border border-border">
                <img src={src} alt="" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
                <div className="absolute inset-0 flex items-center justify-center bg-black/0 opacity-0 transition-all group-hover:bg-black/30 group-hover:opacity-100">
                  <Play className="h-7 w-7 fill-white text-white" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="border-t border-border bg-card/50">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:py-24">
          <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">Creators love it.</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <div key={t.name} className="rounded-2xl border border-border bg-card p-6">
                <div className="flex gap-0.5">
                  {Array.from({ length: 5 }).map((_, i) => <Star key={i} className="h-3.5 w-3.5 fill-ink text-ink" />)}
                </div>
                <p className="mt-3 text-sm leading-relaxed">"{t.text}"</p>
                <div className="mt-4">
                  <p className="text-sm font-semibold">{t.name}</p>
                  <p className="text-xs text-muted-foreground">{t.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-t border-border">
        <div className="mx-auto max-w-6xl px-5 py-16 sm:py-24">
          <div className="text-center">
            <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">Simple pricing.</h2>
            <p className="mt-3 text-muted-foreground">Start free. Upgrade when you're ready.</p>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {PLANS.map((p) => (
              <div key={p.name} className={`relative rounded-2xl border p-6 ${p.featured ? "border-ink bg-ink text-white shadow-xl" : "border-border bg-card"}`}>
                {p.featured && <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-white px-3 py-0.5 text-[10px] font-bold uppercase tracking-wide text-ink">Popular</span>}
                <h3 className="text-base font-semibold">{p.name}</h3>
                <p className={`mt-1 text-xs ${p.featured ? "text-white/70" : "text-muted-foreground"}`}>{p.tagline}</p>
                <p className="mt-4 font-display text-4xl font-extrabold">{p.price}<span className="text-sm font-medium opacity-60">/mo</span></p>
                <ul className="mt-5 space-y-2.5 text-sm">
                  {p.features.map((feat) => (
                    <li key={feat} className="flex items-center gap-2">
                      <Check className={`h-4 w-4 ${p.featured ? "text-white" : "text-ink"}`} /> {feat}
                    </li>
                  ))}
                </ul>
                <Link to="/plans" className={`mt-6 block rounded-full py-2.5 text-center text-sm font-semibold transition-colors ${p.featured ? "bg-white text-ink hover:bg-white/90" : "bg-ink text-white hover:bg-ink/90"}`}>
                  Choose {p.name}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-card/50">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-8 sm:flex-row">
          <Logo />
          <p className="text-xs text-muted-foreground">© {new Date().getFullYear()} Vivomatica AI. Crafted for creators.</p>
          <div className="flex gap-5 text-xs text-muted-foreground">
            <a href="#features" className="hover:text-ink">Features</a>
            <a href="#pricing" className="hover:text-ink">Pricing</a>
            <Link to="/onboarding" className="hover:text-ink">Get started</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}