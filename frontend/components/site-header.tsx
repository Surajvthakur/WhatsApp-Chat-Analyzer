import Link from "next/link";
import { MessageCircle } from "lucide-react";
import { auth, signOut } from "@/auth";

export async function SiteHeader() {
  const session = await auth();

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

          {session ? (
            <div className="flex items-center gap-4">
              <span className="text-xs text-[var(--muted-foreground)] border-r border-[var(--border)] pr-4 py-1 hidden sm:inline-block">
                {session.user?.email}
              </span>
              <form
                action={async () => {
                  "use server";
                  await signOut({ redirectTo: "/" });
                }}
              >
                <button
                  type="submit"
                  className="rounded-lg border border-[var(--border)] px-4 py-1.5 font-medium hover:bg-[var(--muted)] transition-colors cursor-pointer"
                >
                  Sign Out
                </button>
              </form>
            </div>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-[var(--primary)] px-4 py-1.5 font-medium text-[var(--primary-foreground)] transition-opacity hover:opacity-90 cursor-pointer"
            >
              Sign In
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
