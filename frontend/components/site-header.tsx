import Link from "next/link";
import { MessageCircle } from "lucide-react";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--card)]/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <MessageCircle className="h-6 w-6 text-[var(--primary)]" />
          <span>WhatsApp Chat Analyzer</span>
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          <Link
            href="/analyze"
            className="rounded-lg bg-[var(--primary)] px-4 py-2 font-medium text-[var(--primary-foreground)] transition-opacity hover:opacity-90"
          >
            Analyze Chat
          </Link>
        </nav>
      </div>
    </header>
  );
}
