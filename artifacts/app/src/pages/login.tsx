import { useState, type FormEvent } from "react";
import { Link, useLocation } from "wouter";
import { ArrowLeft, ArrowRight, Check, Grid3X3, Loader2, RadioTower, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";

const proofPoints = [
  "Pipeline traces for every production",
  "Human approvals before expensive batches",
  "Scheduled generation and publishing",
];

export default function Login() {
  const [, setLocation] = useLocation();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      setLocation("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-[#f6f5ef] text-[#101010] lg:grid-cols-[1fr_520px]">
      <section className="relative grid min-h-[520px] content-between overflow-hidden border-b border-[#d9d8d0] p-5 pt-6 md:p-10 lg:min-h-screen lg:border-b-0 lg:border-r">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_16%_18%,rgba(216,255,99,0.50),transparent_28%),radial-gradient(circle_at_80%_8%,rgba(16,16,16,0.10),transparent_24%)]" />

        <div className="relative flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-full bg-[#101010] text-[#d8ff63]">
              <Grid3X3 className="h-4 w-4" />
            </span>
            <span className="text-sm font-semibold">Dysentry</span>
          </Link>
          <Link href="/" className="hidden items-center gap-2 rounded-full border border-[#d9d8d0] bg-white px-3 py-2 text-xs font-semibold text-[#5f5d55] md:flex">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back home
          </Link>
        </div>

        <div className="relative py-16 md:py-20">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#d9d8d0] bg-white px-3 py-1.5 text-xs font-semibold text-[#5f5d55]">
            <RadioTower className="h-3.5 w-3.5 text-[#101010]" />
            Private production workspace
          </div>
          <h1 className="max-w-[980px] text-[clamp(4.3rem,9vw,10rem)] font-semibold leading-[0.78] tracking-[-0.08em]">
            {mode === "login" ? "Open your production console." : "Create your production console."}
          </h1>
          <p className="mt-7 max-w-[680px] text-base leading-7 text-[#706f66] md:text-lg">
            {mode === "login"
              ? "Access active generations, checkpoints, generated scenes, schedules, and publishing targets."
              : "Start a Dysentry workspace for prompt-to-episode workflows, approvals, and channel automation."}
          </p>
        </div>

        <div className="relative grid gap-3 md:grid-cols-3">
          {proofPoints.map((point) => (
            <div key={point} className="grid grid-cols-[auto_1fr] gap-3 border-t border-[#d9d8d0] pt-4 text-sm leading-6 text-[#4d4b44]">
              <span className="mt-1 grid h-5 w-5 place-items-center rounded-full bg-[#101010] text-white">
                <Check className="h-3 w-3" />
              </span>
              {point}
            </div>
          ))}
        </div>
      </section>

      <section className="grid min-h-screen content-center bg-[#101010] p-5 text-white md:p-10">
        <div className="mx-auto w-full max-w-[420px]">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-full bg-[#d8ff63] text-[#101010]">
              <Sparkles className="h-5 w-5" />
            </span>
            <div>
              <div className="text-lg font-semibold">Dysentry</div>
              <div className="text-sm text-white/45">Agentic media console</div>
            </div>
          </div>

          <div className="mt-12">
            <div className="grid grid-cols-2 rounded-full border border-white/10 bg-white/[0.04] p-1">
              {(["login", "register"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    setMode(item);
                    setError("");
                  }}
                  className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                    mode === item ? "bg-white text-[#101010]" : "text-white/50 hover:text-white"
                  }`}
                >
                  {item === "login" ? "Sign in" : "Register"}
                </button>
              ))}
            </div>

            <h2 className="mt-8 text-[clamp(3rem,5vw,4.6rem)] font-semibold leading-[0.82] tracking-[-0.075em]">
              {mode === "login" ? "Welcome back." : "Start here."}
            </h2>
            <p className="mt-4 text-sm leading-6 text-white/50">
              {mode === "login"
                ? "Continue your stories, scenes, scheduled runs, and publishes."
                : "Your account owns productions, media refs, jobs, and pipeline history."}
            </p>
          </div>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-white/70">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-12 rounded-[16px] border-white/10 bg-white/[0.06] text-white placeholder:text-white/30"
                placeholder="you@studio.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-white/70">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-12 rounded-[16px] border-white/10 bg-white/[0.06] text-white placeholder:text-white/30"
                placeholder="Minimum 8 characters"
              />
            </div>

            {error ? (
              <div className="rounded-[16px] border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm leading-5 text-red-100">
                {error}
              </div>
            ) : null}

            <Button type="submit" className="h-12 w-full rounded-full bg-[#d8ff63] text-[#101010] hover:bg-[#e4ff8c]" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
              {mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-white/45">
            {mode === "login" ? "New to Dysentry?" : "Already have a workspace?"}{" "}
            <button
              type="button"
              className="font-semibold text-white hover:underline"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
              }}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}

