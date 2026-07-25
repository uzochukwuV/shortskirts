import { Link } from "wouter";
import { ArrowRight, Grid3X3, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export function LandingNav() {
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <header className="fixed left-0 right-0 top-0 z-50 border-b border-white/10 bg-[#080808]/72 backdrop-blur-xl">
      <nav className="grid h-16 w-full grid-cols-[1fr_auto_1fr] items-center px-4 text-white md:px-8">
        <Link href="/" className="flex min-w-0 items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-[#d8ff63] text-[#101010]">
            <Grid3X3 className="h-4 w-4" />
          </span>
          <span className="text-[15px] font-semibold tracking-[-0.03em]">Dysentry</span>
        </Link>

        <div className="hidden rounded-full border border-white/10 bg-white/[0.06] p-1 md:flex">
          {[
            ["Studio", "/dashboard"],
            ["Pricing", "/pricing"],
            ["Gallery", "/gallery"],
          ].map(([label, href]) => (
            <Link key={label} href={href} className="rounded-full px-4 py-2 text-xs font-medium text-white/66 transition hover:bg-white/10 hover:text-white">
              {label}
            </Link>
          ))}
        </div>

        <div className="flex min-w-0 justify-end">
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <span className="hidden max-w-[220px] truncate rounded-full border border-white/10 px-3 py-2 text-xs text-white/60 lg:block">
                {user?.email}
              </span>
              <Link href="/dashboard">
                <Button size="sm" className="rounded-full bg-white text-[#101010] hover:bg-white/90">
                  Studio
                </Button>
              </Link>
              <Button size="sm" variant="ghost" className="hidden rounded-full text-white hover:bg-white/10 md:inline-flex" onClick={() => logout()}>
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Link href="/login">
              <Button size="sm" className="rounded-full bg-white text-[#101010] hover:bg-white/90">
                Enter
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
