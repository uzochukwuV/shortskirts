import { useState } from "react";
import { Link } from "wouter";
import { ArrowRight, CheckCircle2, Zap } from "lucide-react";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";

const PLANS = [
  {
    name: "Starter",
    price: { monthly: 0, annual: 0 },
    desc: "Try the pipeline with a small quota.",
    cta: "Get started free",
    highlight: false,
    limits: "5 videos / month · 1 active series",
    features: ["All workflows", "Story planning", "Video generation", "Character memory"],
  },
  {
    name: "Creator",
    price: { monthly: 29, annual: 23 },
    desc: "For independent creators shipping weekly.",
    cta: "Start Creator plan",
    highlight: true,
    badge: "Most popular",
    limits: "60 videos / month · 5 active series",
    features: ["Everything in Starter", "Scene regeneration", "Approval gates", "Platform exports"],
  },
  {
    name: "Studio",
    price: { monthly: 99, annual: 79 },
    desc: "For agencies and teams producing at scale.",
    cta: "Start Studio plan",
    highlight: false,
    limits: "300 videos / month · Unlimited series",
    features: ["Everything in Creator", "Client brand bibles", "Review links", "Usage tracking"],
  },
  {
    name: "Enterprise",
    price: { monthly: null, annual: null },
    desc: "Custom contract and dedicated support.",
    cta: "Contact us",
    highlight: false,
    limits: "Custom limits · Custom SLA",
    features: ["Dedicated pipeline", "Commercial license", "SOC 2 support", "Onboarding"],
  },
];

const FAQ = [
  ["What counts as a video?", "Each rendered scene clip counts as one video. The assembled episode does not count separately."],
  ["What happens if a render fails?", "Failed renders do not count against your quota. The worker retries the step automatically."],
  ["Can I regenerate a single scene?", "Yes. Regeneration uses one slot for that scene only, not the whole episode."],
  ["Is there a long-term contract?", "No. Monthly and annual plans can be cancelled at any time. Annual saves about 20%."],
];

export default function Pricing() {
  const [annual, setAnnual] = useState(false);

  return (
    <Layout>
      <div className="bg-background">
        <section className="border-b border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-16 text-center md:px-6">
            <div className="inline-flex items-center gap-2 rounded-[12px] border border-border bg-white px-3 py-1 text-[12px] font-medium text-foreground">
              <Zap className="h-3.5 w-3.5 text-[color:#ff5a00]" />
              Simple, transparent pricing
            </div>
            <h1 className="mt-6 text-4xl font-semibold leading-tight text-foreground md:text-5xl">
              Pricing that matches the production loop
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-[15px] leading-7 text-muted-foreground">
              This is priced around recurring video production, approvals, and retries. Not seats, not exports, not vague usage buckets.
            </p>

            <div className="mx-auto mt-8 inline-flex items-center rounded-[10000px] border border-border bg-white p-1">
              <button
                onClick={() => setAnnual(false)}
                className={`rounded-[10000px] px-4 py-1.5 text-sm font-medium ${!annual ? "bg-foreground text-background" : "text-muted-foreground"}`}
              >
                Monthly
              </button>
              <button
                onClick={() => setAnnual(true)}
                className={`rounded-[10000px] px-4 py-1.5 text-sm font-medium ${annual ? "bg-foreground text-background" : "text-muted-foreground"}`}
              >
                Annual <span className="text-[color:#ff5a00]">-20%</span>
              </button>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-[1200px] px-4 py-12 md:px-6">
          <div className="grid gap-5 lg:grid-cols-4">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={`relative flex h-full flex-col rounded-[36px] border p-7 ${
                  plan.highlight ? "border-foreground bg-foreground text-background" : "border-border bg-white"
                }`}
              >
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-[10000px] bg-[color:#ff5a00] px-3 py-1 text-[10px] font-medium uppercase text-white">
                    {plan.badge}
                  </div>
                )}

                <div className="space-y-3">
                  <h2 className={`text-lg font-semibold ${plan.highlight ? "text-background" : "text-foreground"}`}>
                    {plan.name}
                  </h2>
                  <p className={`text-sm leading-6 ${plan.highlight ? "text-background/70" : "text-muted-foreground"}`}>
                    {plan.desc}
                  </p>
                  <div className="flex items-baseline gap-1">
                    {plan.price.monthly === null ? (
                      <span className={`text-3xl font-semibold ${plan.highlight ? "text-background" : "text-foreground"}`}>
                        Custom
                      </span>
                    ) : (
                      <>
                        <span className={`text-3xl font-semibold ${plan.highlight ? "text-background" : "text-foreground"}`}>
                          ${annual ? plan.price.annual : plan.price.monthly}
                        </span>
                        <span className={`text-sm ${plan.highlight ? "text-background/60" : "text-muted-foreground"}`}>/mo</span>
                      </>
                    )}
                  </div>
                  <p className={`text-xs ${plan.highlight ? "text-background/60" : "text-muted-foreground"}`}>
                    {plan.limits}
                  </p>
                </div>

                <ul className="mt-6 flex-1 space-y-2.5">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2">
                      <CheckCircle2 className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${plan.highlight ? "text-[color:#ff5a00]" : "text-foreground"}`} />
                      <span className={`text-xs leading-relaxed ${plan.highlight ? "text-background/80" : "text-muted-foreground"}`}>
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                <Link href={plan.name === "Enterprise" ? "/" : "/dashboard"} className="mt-6">
                  <Button className="w-full" variant={plan.highlight ? "outline" : "default"}>
                    {plan.cta}
                    {plan.name !== "Enterprise" && <ArrowRight className="h-4 w-4" />}
                  </Button>
                </Link>
              </div>
            ))}
          </div>

          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {[
              "Free tier includes real generation",
              "All plans include memory and approvals",
              "No long-term contract below Enterprise",
            ].map((item) => (
              <div key={item} className="rounded-[24px] border border-border bg-white p-4 text-sm text-foreground">
                {item}
              </div>
            ))}
          </div>
        </section>

        <section className="border-t border-border bg-muted/30 py-16">
          <div className="mx-auto max-w-3xl px-4 md:px-6">
            <h2 className="text-center text-3xl font-semibold text-foreground">Frequently asked questions</h2>
            <div className="mt-10 space-y-6">
              {FAQ.map(([q, a]) => (
                <div key={q} className="border-b border-border pb-6 last:border-0 last:pb-0">
                  <h3 className="font-semibold text-foreground">{q}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{a}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}
