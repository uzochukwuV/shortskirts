import { Link } from "wouter";
import { CheckCircle2, Sparkles } from "lucide-react";
import { Layout } from "@/components/layout";
import { Button } from "@/components/ui/button";

const PLANS = [
  {
    name: "Starter",
    price: "$0",
    details: "Small quota for testing the full flow.",
    features: ["Story planning", "Scene preview", "Public gallery"],
  },
  {
    name: "Creator",
    price: "$29",
    details: "For recurring weekly production.",
    features: ["Approval gates", "Version history", "Narration checkpoints"],
    featured: true,
  },
  {
    name: "Studio",
    price: "$99",
    details: "For teams shipping at higher volume.",
    features: ["Multiple workflows", "History tables", "Queue-heavy production"],
  },
];

export default function Pricing() {
  return (
    <Layout>
      <div className="bg-white">
        <section className="border-b border-border">
          <div className="mx-auto max-w-[1200px] px-4 py-12 md:px-6">
            <div className="inline-flex items-center gap-2 rounded-[9999px] border border-border bg-muted px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-[color:#083300]" />
              Plans
            </div>
            <h1 className="mt-6 max-w-3xl font-display text-[54px] leading-[0.88] tracking-[-0.05em] text-foreground">
              Pricing for running a production pipeline, not a demo page.
            </h1>
            <p className="mt-4 max-w-2xl text-[16px] leading-7 text-muted-foreground">
              The tiers are aligned to real usage: planning, approvals, renders, and version history.
            </p>
          </div>
        </section>

        <section className="mx-auto max-w-[1200px] px-4 py-12 md:px-6">
          <div className="grid gap-4 lg:grid-cols-3">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-[16px] border p-6 ${
                  plan.featured ? "border-[color:#083300] bg-[color:#121212] text-white" : "border-border bg-white"
                }`}
              >
                <div className="text-sm font-semibold">{plan.name}</div>
                <div className="mt-3 font-display text-[40px] leading-[1] tracking-[-0.04em]">
                  {plan.price}
                  <span className={`ml-1 text-sm ${plan.featured ? "text-white/60" : "text-muted-foreground"}`}>/mo</span>
                </div>
                <p className={`mt-2 text-sm leading-6 ${plan.featured ? "text-white/70" : "text-muted-foreground"}`}>
                  {plan.details}
                </p>

                <div className="mt-6 space-y-3">
                  {plan.features.map((feature) => (
                    <div key={feature} className={`flex items-start gap-2 text-sm ${plan.featured ? "text-white/80" : "text-foreground"}`}>
                      <CheckCircle2 className="mt-0.5 h-4 w-4 text-[color:#96ff1a]" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>

                <Link href="/login" className="mt-6 block">
                  <Button variant={plan.featured ? "lime" : "outline"} className="w-full">
                    {plan.featured ? "Start Creator" : "Get started"}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </section>
      </div>
    </Layout>
  );
}
