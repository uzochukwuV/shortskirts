import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";
import SiteChrome from "@/components/dysentry/SiteChrome";
import Button from "@/components/dysentry/Button";
import { Image } from "@/components/ui/image";

const tabs = ["Overview", "Characters", "Pipeline", "Publishing", "Analytics"];

const features = [
  {
    tag: "Memory",
    title: "Persistent character & style memory",
    body: "Every character, voice, and visual convention is stored once and recalled across every episode — so your cast stays consistent from scene one to scene fifty.",
    image: "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=900&q=80",
  },
  {
    tag: "Pipeline",
    title: "Checkpointed scene pipeline",
    body: "Draft, request review, approve, and publish — each scene moves through clear approval gates so nothing ships without a human sign-off.",
    image: "https://images.unsplash.com/photo-1505236858219-8359eb29e329?w=900&q=80",
  },
  {
    tag: "Media",
    title: "Mixed-media workflows",
    body: "Compose scenes as video, narrated image stories, or pure voice. Regenerate any element on demand without losing the surrounding context.",
    image: "https://images.unsplash.com/photo-1500916434205-0c77489c6cf7?w=900&q=80",
  },
];

const pipeline = [
  { step: "01", label: "Draft", desc: "Write or generate the scene script" },
  { step: "02", label: "Characters", desc: "Pull consistent cast from memory" },
  { step: "03", label: "Compose", desc: "Assemble media, narration, and timing" },
  { step: "04", label: "Review", desc: "Human-in-the-loop approval gate" },
  { step: "05", label: "Approve", desc: "Lock the scene for publishing" },
  { step: "06", label: "Publish", desc: "Schedule and auto-publish to platforms" },
];

const analyticsPoints = [
  "Per-episode performance dashboards",
  "Platform-level breakdowns",
  "Trend tracking across the full series",
  "Regeneration suggestions based on drop-off",
];

export default function Landing() {
  const [activeTab, setActiveTab] = useState("Overview");

  return (
    <SiteChrome>
      {/* Hero */}
      <section className="mx-auto max-w-[1280px] px-6 pb-20 pt-16">
        <nav className="mb-6 text-[11px] text-steel" style={{ lineHeight: 1.45 }}>
          Home / Platform
        </nav>
        <h1 className="font-display max-w-3xl text-[57px] font-medium leading-[1.12] text-ink">
          Serialized stories,
          <br />
          made to ship.
        </h1>
        <p className="mt-6 max-w-xl text-[16px] text-steel" style={{ lineHeight: 1.5 }}>
          Dysentry helps creators and brands produce serialized short-form stories with consistent characters, approval
          checkpoints, and automated publishing — all tracked with per-episode analytics.
        </p>
        <div className="mt-8 flex items-center gap-3">
          <Link to="/register">
            <Button>
              Start creating <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link to="/dashboard">
            <Button variant="secondary">View studio</Button>
          </Link>
        </div>
        {/* Tab nav */}
        <div className="mt-16 flex items-center gap-8 overflow-x-auto border-b border-mist">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`whitespace-nowrap py-3 text-[16px] transition-colors ${activeTab === tab ? "font-medium text-ink" : "text-steel hover:text-ink"}`}
            >
              {tab}
            </button>
          ))}
        </div>
      </section>

      {/* Feature cards */}
      <section className="mx-auto max-w-[1280px] px-6 py-20">
        <div className="grid gap-6 md:grid-cols-3">
          {features.map((f) => (
            <article key={f.title} className="rounded-lg border border-fog p-4">
              <div className="overflow-hidden rounded-2xl">
                <Image src={f.image} alt={f.title} className="aspect-[4/3] w-full object-cover" fittingType="fill" />
              </div>
              <p className="mt-4 text-[11px] text-steel">Tag: {f.tag}</p>
              <h3 className="mt-1 text-[16px] text-ink" style={{ lineHeight: 1.5 }}>{f.title}</h3>
              <p className="mt-2 text-[14px] text-steel" style={{ lineHeight: 1.5 }}>{f.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Pipeline */}
      <section className="border-y border-mist bg-muted/40">
        <div className="mx-auto max-w-[1280px] px-6 py-20">
          <p className="mb-3 text-[11px] text-steel">How it works</p>
          <h2 className="font-display mb-12 text-[26px] font-medium text-ink" style={{ lineHeight: 1.2 }}>
            From draft to publish, in six gated steps.
          </h2>
          <div className="grid gap-px sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {pipeline.map((p) => (
              <div key={p.step} className="bg-paper p-6">
                <span className="text-[11px] text-steel">{p.step}</span>
                <h3 className="mt-2 text-[16px] font-medium tracking-tight-bold text-ink">{p.label}</h3>
                <p className="mt-1 text-[13px] text-steel" style={{ lineHeight: 1.45 }}>{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Analytics preview */}
      <section className="mx-auto max-w-[1280px] px-6 py-20">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="mb-3 text-[11px] text-steel">Analytics</p>
            <h2 className="font-display mb-4 text-[26px] font-medium text-ink" style={{ lineHeight: 1.2 }}>
              Track engagement, episode by episode.
            </h2>
            <p className="mb-6 text-[16px] text-steel" style={{ lineHeight: 1.5 }}>
              Views, engagement rate, likes, comments, and shares — broken down per episode and per platform, so you know
              what resonates and what to regenerate.
            </p>
            <ul className="space-y-2">
              {analyticsPoints.map((item) => (
                <li key={item} className="flex items-center gap-2 text-[14px] text-ink">
                  <Check className="h-4 w-4 text-ink" /> {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-fog p-6">
            <div className="flex items-end justify-between">
              <div>
                <p className="text-[11px] text-steel">Avg. engagement rate</p>
                <p className="font-display text-[26px] font-medium text-ink">12.4%</p>
              </div>
              <p className="text-[11px] text-steel">Last 7 episodes</p>
            </div>
            <div className="mt-6 flex h-40 items-end gap-2">
              {[40, 55, 48, 70, 62, 85, 78].map((h, i) => (
                <div key={i} className="flex-1 rounded-t-lg bg-ink" style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-[1280px] px-6 py-20">
        <div className="rounded-lg border border-fog px-8 py-16 text-center">
          <h2 className="font-display text-[40px] font-medium text-ink" style={{ lineHeight: 1.12 }}>
            Start your first series today.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-[16px] text-steel" style={{ lineHeight: 1.5 }}>
            Free to start. No credit card required.
          </p>
          <Link to="/register" className="mt-8 inline-block">
            <Button>
              Start creating <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>
    </SiteChrome>
  );
}