import type { ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { Menu, Sparkles, LogOut, UserCircle2 } from "lucide-react";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";
import { useAuth } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/pricing", label: "Pricing" },
];

export function Layout({ children }: { children: ReactNode }) {
  const [location, setLocation] = useLocation();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground font-sans">
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="mx-auto flex h-16 max-w-[1200px] items-center gap-4 px-4 md:px-6">
          <Link href="/" className="flex items-center gap-3 shrink-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-[14px] bg-foreground text-background">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="leading-none">
              <div className="font-semibold text-foreground">StoryForge</div>
              <div className="text-[11px] text-muted-foreground">Series engine</div>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm ml-3">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`font-medium transition-colors ${location.startsWith(item.href) ? "text-foreground" : "text-muted-foreground hover:text-foreground"}`}
              >
                {item.label}
              </Link>
            ))}
            <a
              href="https://qwencloud.com"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Powered by Qwen
            </a>
          </nav>

          <div className="flex-1" />

          <div className="hidden items-center gap-3 md:flex">
            {user ? (
              <>
                <div className="max-w-[240px] truncate text-sm text-muted-foreground">
                  <UserCircle2 className="mr-2 inline h-4 w-4 align-text-bottom" />
                  <span>{user.email}</span>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-muted-foreground hover:text-foreground"
                  onClick={async () => {
                    await logout();
                    setLocation("/");
                  }}
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </Button>
              </>
            ) : (
              <Link href="/login">
                <Button size="sm">Sign in</Button>
              </Link>
            )}
          </div>

          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="md:hidden px-2">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="bg-background">
              <Link href="/" className="mb-8 flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-[14px] bg-foreground text-background">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div className="leading-none">
                  <div className="font-semibold text-foreground">StoryForge</div>
                  <div className="text-[11px] text-muted-foreground">Series engine</div>
                </div>
              </Link>
              <div className="flex flex-col gap-4 text-sm">
                {navItems.map((item) => (
                  <Link key={item.href} href={item.href} className="font-medium text-foreground/70 hover:text-foreground">
                    {item.label}
                  </Link>
                ))}
                {user ? (
                  <button
                    className="text-left font-medium text-foreground/70 hover:text-foreground"
                    onClick={async () => {
                      await logout();
                      setLocation("/");
                    }}
                  >
                    Sign out
                  </button>
                ) : (
                  <Link href="/login" className="font-medium text-foreground/70 hover:text-foreground">
                    Sign in
                  </Link>
                )}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <main className="flex-1 flex flex-col">{children}</main>

      <footer className="border-t border-border bg-background py-6">
        <div className="mx-auto flex max-w-[1200px] flex-col items-center justify-between gap-2 px-4 text-xs text-muted-foreground md:flex-row md:px-6">
          <div className="flex items-center gap-2">
            <div className="flex h-5 w-5 items-center justify-center rounded-[7px] bg-foreground text-background">
              <Sparkles className="h-2.5 w-2.5" />
            </div>
            <span className="font-medium text-foreground">StoryForge</span>
          </div>
          <span>AI showrunner for serialized video with Qwen, Wan, B2, and CockroachDB.</span>
          <nav className="flex gap-4">
            <Link href="/pricing" className="transition-colors hover:text-foreground">Pricing</Link>
            <Link href="/dashboard" className="transition-colors hover:text-foreground">Dashboard</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
