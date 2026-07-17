import { useState, type FormEvent } from "react";
import { useLocation } from "wouter";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";

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
    <main className="min-h-screen bg-white px-4 py-6 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-48px)] max-w-[1200px] gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-[16px] border border-border bg-[color:#121212] p-6 text-white md:p-8">
          <div className="inline-flex items-center gap-2 rounded-[9999px] border border-white/10 bg-white/5 px-3 py-1 text-[11px] uppercase tracking-[0.16em] text-white/70">
            <Sparkles className="h-3.5 w-3.5 text-[color:#96ff1a]" />
            Private workspace
          </div>

          <h1 className="mt-8 max-w-2xl font-display text-[54px] leading-[0.88] tracking-[-0.05em] text-white">
            {mode === "login" ? "Sign in to your studio." : "Create your studio."}
          </h1>
          <p className="mt-4 max-w-xl text-[16px] leading-7 text-white/70">
            {mode === "login"
              ? "Open your productions, version history, and render console."
              : "Start a private workspace for story briefs, approvals, and generated media."}
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {["Outline first", "Generate next", "Review live"].map((item) => (
              <div key={item} className="rounded-[16px] border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/80">
                {item}
              </div>
            ))}
          </div>
        </section>

        <Card className="self-center">
          <CardContent className="p-6 md:p-8">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-[10px] border border-border bg-[color:#96ff1a] text-[color:#083300]">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <div className="text-lg font-semibold text-foreground">StoryForge</div>
                <div className="text-sm text-muted-foreground">Production console</div>
              </div>
            </div>

            <div className="mt-8 space-y-2">
              <div className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                {mode === "login" ? "Welcome back" : "Start here"}
              </div>
              <h2 className="font-display text-[40px] leading-[1] tracking-[-0.04em] text-foreground">
                {mode === "login" ? "Sign in" : "Create account"}
              </h2>
              <p className="text-sm leading-6 text-muted-foreground">
                {mode === "login"
                  ? "Access your productions, checkpoints, and generated scenes."
                  : "Set up the account that will own your productions and media."}
              </p>
            </div>

            <form onSubmit={submit} className="mt-8 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" variant="lime" className="w-full" disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                {mode === "login" ? "Sign in" : "Create account"}
              </Button>
            </form>

            <div className="mt-5 text-center text-sm text-muted-foreground">
              {mode === "login" ? "New here?" : "Already have an account?"}{" "}
              <button
                type="button"
                className="font-medium text-foreground hover:underline"
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError("");
                }}
              >
                {mode === "login" ? "Create an account" : "Sign in"}
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
