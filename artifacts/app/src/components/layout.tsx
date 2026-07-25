import type { ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { ChevronRight, Clapperboard, LibraryBig, Menu, Sparkles, LogOut } from "lucide-react";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";
import { useAuth } from "@/lib/auth";

const navItems = [
  { href: "/", label: "Reel" },
  { href: "/dashboard", label: "Studio" },
  { href: "/pricing", label: "Plans" },
];

export function Layout({ children }: { children: ReactNode }) {
  const [location, setLocation] = useLocation();
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b border-border bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="mx-auto flex h-16 max-w-[1280px] items-center gap-4 px-4 md:px-6">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-[12px] border border-border bg-[color:#96ff1a] text-[color:#083300]">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="leading-none">
              <div className="text-[15px] font-semibold tracking-tight">Dysentry</div>
              <div className="text-[11px] text-muted-foreground">production workspace</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-2 md:flex">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-[9999px] px-3 py-1.5 text-sm font-medium transition-colors ${
                  location === item.href || location.startsWith(`${item.href}/`)
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="flex-1" />

          <div className="hidden items-center gap-3 md:flex">
            {isAuthenticated ? (
              <>
                <div className="flex items-center gap-2 rounded-[9999px] border border-border bg-muted px-3 py-1.5 text-[12px] text-muted-foreground">
                  <LibraryBig className="h-3.5 w-3.5" />
                  <span className="max-w-[180px] truncate">{user?.email}</span>
                </div>
                <Link href="/dashboard">
                  <Button size="sm" variant="outline">
                    Studio
                  </Button>
                </Link>
                <Button
                  size="sm"
                  variant="ghost"
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
              <>
                <Link href="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground">
                  Sign in
                </Link>
                <Link href="/login">
                  <Button size="sm" variant="lime">
                    Start workspace
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </Link>
              </>
            )}
          </div>

            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="bg-white">
                <div className="mb-8 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-[12px] border border-border bg-[color:#96ff1a] text-[color:#083300]">
                  <Clapperboard className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-sm font-semibold">Dysentry</div>
                  <div className="text-[11px] text-muted-foreground">production workspace</div>
                </div>
              </div>
              <div className="flex flex-col gap-4">
                {navItems.map((item) => (
                  <Link key={item.href} href={item.href} className="text-sm font-medium text-foreground">
                    {item.label}
                  </Link>
                ))}
                {isAuthenticated ? (
                  <>
                    <Link href="/dashboard" className="text-sm font-medium text-foreground">
                      Studio
                    </Link>
                    <button
                      type="button"
                      className="text-left text-sm font-medium text-muted-foreground"
                      onClick={async () => {
                        await logout();
                        setLocation("/");
                      }}
                    >
                      Sign out
                    </button>
                  </>
                ) : (
                  <Link href="/login" className="text-sm font-medium text-foreground">
                    Sign in
                  </Link>
                )}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1280px] px-4 py-6 md:px-6">{children}</main>
    </div>
  );
}
