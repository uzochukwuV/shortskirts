import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, ArrowRight, ArrowLeft } from "lucide-react";
import Logo from "@/components/Logo";
import { cn } from "@/lib/utils";

const PLANS = [
  {
    name: "Starter",
    price: "$0",
    period: "/mo",
    tagline: "For trying things out",
    features: ["10 renders / month", "720p exports", "Standard rendering", "Watermark"],
  },
  {
    name: "Creator",
    price: "$24",
    period: "/mo",
    tagline: "For serious creators",
    features: ["Unlimited renders", "1080p exports", "Chat-to-edit", "No watermark", "Priority rendering"],
    featured: true,
  },
  {
    name: "Studio",
    price: "$79",
    period: "/mo",
    tagline: "For teams & brands",
    features: ["Everything in Creator", "4K exports", "Brand presets", "Team seats", "Dedicated support"],
  },
];

export default function Plans() {
  const [selected, setSelected] = useState("Creator");
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="flex h-16 items-center justify-between px-5">
        <Logo />
        <Link to="/onboarding" className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-ink">
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>
      </header>

      <section className="mx-auto max-w-5xl px-5 py-8 sm:py-14">
        <div className="text-center">
          <h1 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl">Choose your plan.</h1>
          <p className="mt-3 text-muted-foreground">Pick a plan to continue. You can change it anytime.</p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-3">
          {PLANS.map((p, i) => {
            const active = selected === p.name;
            return (
              <motion.button
                key={p.name}
                onClick={() => setSelected(p.name)}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                className={cn(
                  "relative flex flex-col rounded-2xl border p-6 text-left transition-all",
                  active
                    ? p.featured
                      ? "border-ink ring-2 ring-ink"
                      : "border-ink ring-2 ring-ink"
                    : "border-border bg-card hover:border-ink/30"
                )}
              >
                {p.featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-ink px-3 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">Popular</span>
                )}
                <h3 className="text-base font-semibold">{p.name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">{p.tagline}</p>
                <p className="mt-4 font-display text-4xl font-extrabold">
                  {p.price}<span className="text-sm font-medium text-muted-foreground">{p.period}</span>
                </p>
                <ul className="mt-5 flex-1 space-y-2.5 text-sm">
                  {p.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-2">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-ink" /> {feat}
                    </li>
                  ))}
                </ul>
                <div className={cn("mt-6 flex items-center justify-center gap-2 rounded-full py-2.5 text-sm font-semibold transition-colors", active ? "bg-ink text-white" : "bg-secondary text-muted-foreground")}>
                  {active ? "Selected" : "Select"}
                </div>
              </motion.button>
            );
          })}
        </div>

        <div className="mt-8 flex justify-center">
          <button
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-2 rounded-full bg-ink px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-ink/10 transition-transform hover:scale-[1.02]"
          >
            Continue with {selected} <ArrowRight className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-4 text-center text-xs text-muted-foreground">No charge until your trial ends. Cancel anytime.</p>
      </section>
    </div>
  );
}