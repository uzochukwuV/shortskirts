import { Link, useLocation } from "wouter";
import { PlaySquare, LayoutDashboard, Menu, Flame } from "lucide-react";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 max-w-screen-2xl items-center">
          <div className="mr-4 hidden md:flex">
            <Link href="/" className="mr-6 flex items-center space-x-2">
              <Flame className="h-6 w-6 text-primary" />
              <span className="hidden font-display font-bold sm:inline-block">
                StoryForge
              </span>
            </Link>
            <nav className="flex items-center space-x-6 text-sm font-medium">
              <Link
                href="/dashboard"
                className={`transition-colors hover:text-foreground/80 ${
                  location === "/dashboard" ? "text-foreground" : "text-foreground/60"
                }`}
              >
                Dashboard
              </Link>
            </nav>
          </div>
          <Sheet>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                className="mr-2 px-0 text-base hover:bg-transparent focus-visible:bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 md:hidden"
              >
                <Menu className="h-5 w-5" />
                <span className="sr-only">Toggle Menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="pr-0">
              <Link href="/" className="flex items-center space-x-2 mb-8">
                <Flame className="h-6 w-6 text-primary" />
                <span className="font-display font-bold">StoryForge</span>
              </Link>
              <div className="flex flex-col space-y-3">
                <Link href="/dashboard" className="text-foreground/70 hover:text-foreground">
                  Dashboard
                </Link>
              </div>
            </SheetContent>
          </Sheet>
          <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
            <div className="w-full flex-1 md:w-auto md:flex-none">
              {/* Search or other header elements could go here */}
            </div>
            <nav className="flex items-center">
              <Link href="/dashboard">
                <Button size="sm" className="font-display uppercase tracking-wider text-xs font-bold">
                  Launch App
                </Button>
              </Link>
            </nav>
          </div>
        </div>
      </header>
      <main className="flex-1 flex flex-col">{children}</main>
    </div>
  );
}
