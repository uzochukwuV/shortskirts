import { Link } from "wouter";
import { ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { LandingNav } from "@/components/landing/landing-nav";
import { Button } from "@/components/ui/button";

const plans = [
  {
    name: "Starter",
    price: "$0",
    detail: "Validate your first production flow.",
    features: ["Outline generation", "Public gallery preview", "Manual publishing"],
  },
  {
    name: "Creator",
    price: "$29",
    detail: "Run recurring story and content channels.",
    features: ["Approval checkpoints", "Version history", "Scheduled runs", "Mock and social publish targets"],
    featured: true,
  },
  {
    name: "Studio",
    price: "$99",
    detail: "Operate higher-volume production queues.",
    features: ["Multiple workflows", "Worker partitioning", "Pipeline trace APIs", "Admin analytics"],
  },
];

export default function Pricing() {
  return (
    <main className="min-h-screen bg-[#080808] text-white">
      <LandingNav />

      <section className="grid min-h-[520px] border-b border-white/10 pt-16 lg:grid-cols-[1fr_1fr]">
        <div className="grid content-end border-b border-white/10 p-6 pb-10 md:p-10 lg:border-b-0 lg:border-r">
          <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-xs text-white/65">
            <Sparkles className="h-3.5 w-3.5 text-[#d8ff63]" />
            Plans
          </div>
          <h1 className="max-w-[760px] text-[clamp(4rem,8vw,9rem)] font-semibold leading-[0.78] tracking-[-0.075em]">
            Pricing for production loops.
          </h1>
        </div>
        <div className="grid content-end p-6 pb-10 md:p-10">
          <p className="max-w-[680px] text-lg leading-8 text-white/58">
            Dysentry is built for creators who need repeatable media operations: planning, rendering, approval,
            scheduling, and publishing from one traced backend.
          </p>
        </div>
      </section>

      <section className="grid border-b border-white/10 lg:grid-cols-3">
        {plans.map((plan) => (
          <article
            key={plan.name}
            className={`grid min-h-[520px] content-between border-b border-white/10 p-6 md:p-8 lg:border-b-0 lg:border-r ${
              plan.featured ? "bg-[#d8ff63] text-[#101010]" : "bg-white/[0.035] text-white"
            }`}
          >
            <div>
              <div className={`text-sm font-semibold ${plan.featured ? "text-[#101010]/60" : "text-white/45"}`}>{plan.name}</div>
              <div className="mt-8 text-[clamp(4rem,7vw,8rem)] font-semibold leading-[0.78] tracking-[-0.075em]">
                {plan.price}
                <span className="ml-2 text-base tracking-[-0.02em]">/mo</span>
              </div>
              <p className={`mt-6 max-w-[360px] text-sm leading-6 ${plan.featured ? "text-[#101010]/68" : "text-white/55"}`}>{plan.detail}</p>
            </div>

            <div>
              <div className="grid gap-3">
                {plan.features.map((feature) => (
                  <div key={feature} className="grid grid-cols-[auto_1fr] gap-3 text-sm">
                    <CheckCircle2 className={`mt-0.5 h-4 w-4 ${plan.featured ? "text-[#101010]" : "text-[#d8ff63]"}`} />
                    <span className={plan.featured ? "text-[#101010]/76" : "text-white/68"}>{feature}</span>
                  </div>
                ))}
              </div>
              <Link href="/login" className="mt-8 inline-flex">
                <Button className={`rounded-full px-6 ${plan.featured ? "bg-[#101010] text-white hover:bg-[#292929]" : "bg-white text-[#101010] hover:bg-white/90"}`}>
                  {plan.featured ? "Start Creator" : "Get started"}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}

