import { Link, useLocation } from "wouter";
import { Menu, Sparkles, LogOut, UserCircle2 } from "lucide-react";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";
import { useAuth } from "@/lib/auth";

export function Layout({ children }: { children: React.ReactNode }) {
  const [location, setLocation] = useLocation();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-white text-gray-900 flex flex-col font-sans">
      <header className="sticky top-0 z-50 w-full border-b border-gray-100 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="container flex h-14 max-w-screen-2xl items-center gap-4 px-4 md:px-6">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-violet-600">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900 tracking-tight">StoryForge</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm ml-2">
            {[
              { href: "/dashboard", label: "Dashboard" },
              { href: "/pricing", label: "Pricing" },
            ].map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`transition-colors font-medium ${
                  location.startsWith(n.href)
                    ? "text-violet-600"
                    : "text-gray-500 hover:text-gray-900"
                }`}
              >
                {n.label}
              </Link>
            ))}
            <a
              href="https://qwencloud.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-gray-900 transition-colors font-medium"
            >
              Powered by Qwen
            </a>
          </nav>

          <div className="flex-1" />

          <div className="hidden md:flex items-center gap-3">
            {user ? (
              <>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <UserCircle2 className="h-4 w-4" />
                  <span>{user.email}</span>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-gray-600 hover:text-gray-900"
                  onClick={async () => {
                    await logout();
                    setLocation("/");
                  }}
                >
                  <LogOut className="mr-2 h-4 w-4" /> Sign out
                </Button>
              </>
            ) : (
              <Link href="/login">
                <Button size="sm" className="bg-gray-900 hover:bg-gray-700 text-white font-medium px-4 rounded-lg text-sm">
                  Sign in
                </Button>
              </Link>
            )}
          </div>

          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="md:hidden px-2">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="bg-white">
              <Link href="/" className="flex items-center gap-2 mb-8">
                <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-violet-600">
                  <Sparkles className="h-4 w-4 text-white" />
                </div>
                <span className="font-semibold">StoryForge</span>
              </Link>
              <div className="flex flex-col gap-4 text-sm">
                <Link href="/dashboard" className="text-gray-700 hover:text-gray-900 font-medium">Dashboard</Link>
                <Link href="/pricing" className="text-gray-700 hover:text-gray-900 font-medium">Pricing</Link>
                {user ? (
                  <button
                    className="text-left text-gray-700 hover:text-gray-900 font-medium"
                    onClick={async () => {
                      await logout();
                      setLocation("/");
                    }}
                  >
                    Sign out
                  </button>
                ) : (
                  <Link href="/login" className="text-gray-700 hover:text-gray-900 font-medium">Sign in</Link>
                )}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <main className="flex-1 flex flex-col">{children}</main>

      <footer className="border-t border-gray-100 bg-white py-6">
        <div className="container px-4 md:px-6 flex flex-col md:flex-row items-center justify-between gap-2 text-xs text-gray-400">
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-4 rounded bg-violet-600 flex items-center justify-center">
              <Sparkles className="h-2.5 w-2.5 text-white" />
            </div>
            <span className="font-medium text-gray-500">StoryForge</span>
          </div>
          <span>AI Showrunner · Qwen Cloud · Wan 2.7 · Backblaze B2 · CockroachDB</span>
          <nav className="flex gap-4">
            <Link href="/pricing" className="hover:text-gray-600 transition-colors">Pricing</Link>
            <Link href="/dashboard" className="hover:text-gray-600 transition-colors">Dashboard</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
