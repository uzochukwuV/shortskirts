import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, Wand2, MessageSquareText, Share2 } from "lucide-react";
import Logo from "@/components/Logo";

const STEPS = [
  { icon: Wand2, title: "Create", desc: "Describe a scene and render it." },
  { icon: MessageSquareText, title: "Refine", desc: "Edit through natural conversation." },
  { icon: Share2, title: "Publish", desc: "Export straight to social." },
];

export default function Onboarding() {
  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="flex h-16 items-center justify-between px-5">
        <Logo />
        <Link to="/landing" className="text-sm font-medium text-muted-foreground hover:text-ink">Back</Link>
      </header>

      <section className="mx-auto grid max-w-6xl items-center gap-10 px-5 py-10 lg:grid-cols-2 lg:py-20">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" /> Welcome
          </span>
          <h1 className="mt-5 font-display text-4xl font-extrabold leading-[1.05] tracking-tight text-balance sm:text-5xl">
            Make cinematic video<br />with your words.
          </h1>
          <p className="mt-5 max-w-md text-base text-muted-foreground sm:text-lg">
            Vivomatica AI is your pocket film studio. Prompt, chat to refine, and publish — no editing skills required.
          </p>

          <div className="mt-8 space-y-3">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              return (
                <motion.div
                  key={s.title}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                  className="flex items-center gap-3"
                >