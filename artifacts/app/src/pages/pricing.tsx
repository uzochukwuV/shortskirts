import { useState } from "react";
import { Link } from "wouter";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { CheckCircle2, ArrowRight, Zap } from "lucide-react";

const PLANS = [
  {
    name: "Starter",
    price: { monthly: 0, annual: 0 },
    desc: "Try the pipeline. No credit card required.",
    cta: "Get started free",
    highlight: false,
    limits: "5 videos / month · 1 active series · 2 GB storage",
    features: [
      "All 5 workflow types",
      "6 production templates",
      "Qwen Cloud story planning",
      "Wan 2.7 video generation",
      "Character & brand memory",
      "Backblaze B2 storage",
      "1 approval gate per run",
    ],
  },
  {
    name: "Creator",
    price: { monthly: 29, annual: 23 },
    desc: "For indie creators shipping weekly content.",
    cta: "Start Creator plan",
    highlight: true,
    badge: "Most popular",
    limits: "60 videos / month · 5 active series · 50 GB storage",
    features: [
      "Everything in Starter",
      "Granular scene regeneration",
      "Per-scene approval gates",
      "TikTok / Reels / Shorts export",
      "Caption & post copy output",
      "Priority render queue",
      "Character ref swap",
      "Tone & aspect ratio variants",
    ],
  },
  {
    name: "Studio",
    price: { monthly: 99, annual: 79 },
    desc: "For agencies and teams producing at scale.",
    cta: "Start Studio plan",
    highlight: false,
    limits: "300 videos / month · Unlimited series · 500 GB storage",
    features: [
      "Everything in Creator",
      "Unlimited team seats",
      "Brand bible per client",
      "Shareable review links",
      "Version history",
      "Usage & cost per client",
      "API access",
      "Export manifests",
      "Custom model parameters",
    ],
  },
  {
    name: "Enterprise",
    price: { monthly: null, annual: null },
    desc: "Custom contract. SLA. Dedicated infrastructure.",
    cta: "Contact us",
    highlight: false,
    limits: "Custom limits · Custom SLA · On-prem option",
    features: [
      "Everything in Studio",
      "Dedicated render pipeline",
      "Custom model fine-tuning",
      "Commercial license",
      "99.9% uptime SLA",
      "SOC 2 compliance",
      "Slack / email support",
      "Onboarding call",
    ],
  },
];

const FAQ = [
  {
    q: "What counts as a 'video'?",
    a: "Each rendered scene clip counts as one video. An episode with 5 scenes uses 5 of your monthly quota. The assembled episode does not count separately.",
  },
  {
    q: "What happens if a render fails?",
    a: "Failed renders do not count against your quota. We retry automatically and only bill for successful generations.",
  },
  {
    q: "Can I regenerate a single scene without using more quota?",
    a: "Regeneration of a scene uses one additional quota slot. Approval-gate rejections before any render do not count.",
  },
  {
    q: "Is there a long-term contract?",
    a: "No. All plans are monthly or annual, cancel anytime. Annual plans save roughly 20%.",
  },
  {
    q: "What models does StoryForge use?",
    a: "Story planning and character prompts use Qwen Cloud (DashScope) — Qwen-Plus primary, Qwen-Turbo fallback. Video generation uses Wan 2.7 via DashScope or AIML. All media is stored in Backblaze B2.",
  },
];

export default function Pricing() {
  const [annual, setAnnual] = useState(false);

  return (
    <Layout>
      <div className="bg-white min-h-screen">

        {/* Header */}
        <div className="pt-16 pb-12 text-center border-b border-gray-100 bg-gradient-to-b from-violet-50/50 to-white">
          <div className="inline-flex items-center gap-1.5 text-xs font-medium text-violet-700 bg-violet-50 border border-violet-200 rounded-full px-3 py-1 mb-6">
            <Zap className="h-3 w-3" /> Simple, transparent pricing
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            Pricing that scales with your production
          </h1>
          <p className="text-gray-500 max-w-md mx-auto mb-8">
            Priced per video minute generated — not per seat or per "export." No surprise bills.
          </p>

          {/* Toggle */}
          <div className="inline-flex items-center bg-gray-100 rounded-full p-1 gap-1">
            <button
              onClick={() => setAnnual(false)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${!annual ? "bg-white shadow-sm text-gray-900" : "text-gray-500"}`}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${annual ? "bg-white shadow-sm text-gray-900" : "text-gray-500"}`}
            >
              Annual <span className="text-violet-600 font-semibold">−20%</span>
            </button>
          </div>
        </div>

        {/* Plans grid */}
        <div className="container px-4 md:px-6 py-12 max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {PLANS.map(plan => (
              <div
                key={plan.name}
                className={`relative rounded-2xl p-6 flex flex-col ${
                  plan.highlight
                    ? "bg-gray-900 border-2 border-violet-500 shadow-xl"
                    : "bg-white border border-gray-200"
                }`}
              >
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-violet-600 text-white text-[10px] font-semibold uppercase tracking-widest px-3 py-1 rounded-full">
                    {plan.badge}
                  </div>
                )}

                <div className="mb-5">
                  <h3 className={`font-bold text-lg mb-1 ${plan.highlight ? "text-white" : "text-gray-900"}`}>
                    {plan.name}
                  </h3>
                  <p className={`text-sm mb-4 ${plan.highlight ? "text-gray-400" : "text-gray-500"}`}>
                    {plan.desc}
                  </p>
                  <div className="flex items-baseline gap-1">
                    {plan.price.monthly === null ? (
                      <span className={`text-3xl font-bold ${plan.highlight ? "text-white" : "text-gray-900"}`}>Custom</span>
                    ) : (
                      <>
                        <span className={`text-3xl font-bold ${plan.highlight ? "text-white" : "text-gray-900"}`}>
                          ${annual ? plan.price.annual : plan.price.monthly}
                        </span>
                        <span className={`text-sm ${plan.highlight ? "text-gray-400" : "text-gray-400"}`}>/mo</span>
                      </>
                    )}
                  </div>
                  <p className={`text-[11px] mt-1 ${plan.highlight ? "text-gray-500" : "text-gray-400"}`}>
                    {plan.limits}
                  </p>
                </div>

                <ul className="space-y-2.5 flex-1 mb-6">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-start gap-2">
                      <CheckCircle2 className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${plan.highlight ? "text-violet-400" : "text-violet-500"}`} />
                      <span className={`text-xs leading-relaxed ${plan.highlight ? "text-gray-300" : "text-gray-600"}`}>{f}</span>
                    </li>
                  ))}
                </ul>

                <Link href={plan.name === "Enterprise" ? "/" : "/dashboard"}>
                  <Button
                    className={`w-full rounded-xl text-sm font-medium ${
                      plan.highlight
                        ? "bg-violet-600 hover:bg-violet-700 text-white"
                        : plan.name === "Starter"
                        ? "bg-gray-100 hover:bg-gray-200 text-gray-900"
                        : "bg-gray-900 hover:bg-gray-700 text-white"
                    }`}
                  >
                    {plan.cta} {plan.name !== "Enterprise" && <ArrowRight className="ml-2 h-3.5 w-3.5" />}
                  </Button>
                </Link>
              </div>
            ))}
          </div>

          {/* Feature comparison note */}
          <div className="mt-10 grid md:grid-cols-3 gap-4 text-center">
            {[
              { label: "Free includes", value: "5 rendered videos/mo — real Qwen + Wan generation, no watermarks" },
              { label: "All plans include", value: "Character memory, brand bibles, B2 storage, approval gates" },
              { label: "Cancel any time", value: "Monthly billing, no contracts below Enterprise tier" },
            ].map(n => (
              <div key={n.label} className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">{n.label}</div>
                <p className="text-sm text-gray-600 leading-relaxed">{n.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ */}
        <div className="border-t border-gray-100 bg-gray-50 py-16">
          <div className="container px-4 md:px-6 max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">Frequently asked questions</h2>
            <div className="space-y-6">
              {FAQ.map(item => (
                <div key={item.q} className="border-b border-gray-200 pb-6 last:border-0 last:pb-0">
                  <h3 className="font-semibold text-gray-900 mb-2">{item.q}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{item.a}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
