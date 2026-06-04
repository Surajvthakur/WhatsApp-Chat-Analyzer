"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { MessageCircle } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function SiteHeader() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const handleSignOut = () => {
    logout();
    router.push("/");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--card)]/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <MessageCircle className="h-6 w-6 text-[var(--primary)]" />
          <span>WhatsApp Chat Analyzer</span>
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link
            href="/analyze"
            className="font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
          >
            Analyze Chat
          </Link>

          {user ? (
            <div className="flex items-center gap-3">
              <span className="text-xs text-[var(--muted-foreground)] border-r border-[var(--border)] pr-3 py-1 hidden md:inline-block">
                {user.email}
              </span>
              <button
                onClick={handleSignOut}
                className="rounded-lg border border-[var(--border)] px-3.5 py-1.5 text-xs sm:text-sm font-medium hover:bg-[var(--muted)] transition-colors cursor-pointer"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-[var(--primary)] px-4 py-1.5 font-medium text-[var(--primary-foreground)] transition-opacity hover:opacity-90 cursor-pointer"
            >
              Login / Register
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
