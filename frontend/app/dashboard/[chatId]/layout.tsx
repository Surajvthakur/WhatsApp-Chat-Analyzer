"use client";

import { use } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Bot, 
  ArrowLeft, 
  Menu, 
  X,
  MessageCircle
} from "lucide-react";
import { useState } from "react";

interface DashboardLayoutProps {
  children: React.ReactNode;
  params: Promise<{ chatId: string }>;
}

export default function DashboardLayout({
  children,
  params,
}: DashboardLayoutProps) {
  const { chatId } = use(params);
  const pathname = usePathname();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const links = [
    {
      href: `/dashboard/${chatId}`,
      label: "Analytics",
      icon: LayoutDashboard,
      active: pathname === `/dashboard/${chatId}`,
    },
    {
      href: `/dashboard/${chatId}/chat`,
      label: "Ask AI",
      icon: Bot,
      active: pathname === `/dashboard/${chatId}/chat`,
    },
  ];

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col md:flex-row bg-[var(--background)]">
      {/* Mobile Header/Navbar */}
      <div className="flex h-14 items-center justify-between border-b border-[var(--border)] bg-[var(--card)] px-4 md:hidden">
        <div className="flex items-center gap-2 font-semibold">
          <MessageCircle className="h-5 w-5 text-[var(--primary)]" />
          <span className="text-sm">Dashboard</span>
        </div>
        <button
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="rounded-lg p-1.5 hover:bg-[var(--muted)] text-[var(--muted-foreground)] focus:outline-none"
        >
          {isMobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden backdrop-blur-xs transition-opacity duration-200"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Mobile Drawer Sidebar */}
      <aside
        className={`fixed bottom-0 top-14 left-0 z-50 w-64 transform border-r border-[var(--border)] bg-[var(--card)] p-4 transition-transform duration-200 ease-in-out md:hidden ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col justify-between">
          <div className="space-y-4">
            <div className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider px-2">
              Menu
            </div>
            <nav className="space-y-1">
              {links.map((link) => {
                const Icon = link.icon;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setIsMobileOpen(false)}
                    className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                      link.active
                        ? "bg-[var(--primary)]/10 text-[var(--primary)] shadow-xs"
                        : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${link.active ? "text-[var(--primary)]" : ""}`} />
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="pt-4 border-t border-[var(--border)]">
            <Link
              href="/analyze"
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Exit Workspace
            </Link>
          </div>
        </div>
      </aside>

      {/* Desktop Sidebar (persistent) */}
      <aside className="hidden w-64 border-r border-[var(--border)] bg-[var(--card)] p-5 md:flex md:flex-col md:justify-between sticky top-14 h-[calc(100vh-3.5rem)] shrink-0">
        <div className="space-y-6">
          <div className="text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider px-3">
            Navigation
          </div>
          <nav className="space-y-1">
            {links.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-all ${
                    link.active
                      ? "bg-[var(--primary)]/10 text-[var(--primary)] shadow-sm"
                      : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]"
                  }`}
                >
                  <Icon className={`h-5 w-5 ${link.active ? "text-[var(--primary)]" : ""}`} />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="pt-4 border-t border-[var(--border)]">
          <Link
            href="/analyze"
            className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
            Exit Workspace
          </Link>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-x-hidden p-6 md:p-8 animate-in fade-in duration-300">
        {children}
      </main>
    </div>
  );
}
