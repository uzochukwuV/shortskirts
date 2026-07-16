import { useState } from "react";
import { useLocation } from "wouter";
import { BadgeCheck, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";

export default function Login() {
  const [, setLocation] = useLocation();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      setLocation("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto grid w-full max-w-[1100px] gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-[36px] border border-border bg-white p-8 md:p-10">
          <div className="inline-flex items-center gap-2 rounded-[12px] border border-border bg-muted px-3 py-1 text-[12px] font-medium text-foreground">
            <BadgeCheck className="h-3.5 w-3.5 text-[color:#ff5a00]" />
            Protected workspace
          </div>

          <div className="mt-8 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-foreground text-background">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="text-lg font-semibold text-foreground">StoryForge</div>
              <div className="text-sm text-muted-foreground">Series engine</div>
            </div>
          </div>

          <h1 className="mt-8 max-w-xl text-4xl font-semibold leading-[1.08] text-foreground md:text-5xl">
            {mode === "login" ? "Sign in to your production workspace" : "Create your workspace"}
          </h1>
          <p className="mt-4 max-w-xl text-[15px] leading-7 text-muted-foreground">
            {mode === "login"
              ? "Access your productions, approvals, and generated media."
              : "Set up a private workspace for briefs, outlines, approvals, and renders."}
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              "One brief to outline",
              "Outline to scenes",
              "Scenes to export",
            ].map((item) => (
              <div key={item} className="rounded-[24px] border border-border bg-background px-4 py-3 text-sm text-foreground">
                {item}
              </div>
            ))}
          </div>
        </section>

        <Card className="border-border">
          <CardHeader className="space-y-4">
            <div className="inline-flex w-fit items-center gap-2 rounded-[12px] border border-border bg-muted px-3 py-1 text-[12px] font-medium text-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-[color:#ff5a00]" />
              {mode === "login" ? "Welcome back" : "Start here"}
            </div>
            <div>
              <CardTitle>{mode === "login" ? "Sign in" : "Create an account"}</CardTitle>
              <CardDescription>
                {mode === "login"
                  ? "Access your productions, bibles, and generated media."
                  : "Start a private workspace for your AI video pipeline."}
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
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
              <Button type="submit" className="w-full" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {mode === "login" ? "Sign in" : "Create account"}
              </Button>
            </form>

            <div className="mt-5 text-center text-sm text-muted-foreground">
              {mode === "login" ? "New to StoryForge?" : "Already have an account?"}{" "}
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
