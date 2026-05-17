"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { Mail, Loader2, CheckCircle2, AlertCircle, ArrowRight, MessageCircle } from "lucide-react";

export default function LoginPage() {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await signIn("resend", {
        email,
        redirect: false,
        callbackUrl: "/analyze", // Default landing after link click
      });

      if (result?.error) {
        if (result.error.includes("Configuration")) {
          setError("Database or email provider configuration error. Please ensure the Resend API Key is set correctly.");
        } else {
          setError(result.error);
        }
      } else {
        setIsSuccess(true);
      }
    } catch (err: any) {
      setError(err?.message || "An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-6 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-8 text-center shadow-2xl backdrop-blur-md">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--primary)]/10 text-[var(--primary)]">
            <CheckCircle2 className="h-10 w-10 animate-bounce" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold tracking-tight">Check your email</h2>
            <p className="text-sm text-[var(--muted-foreground)]">
              We have sent a secure sign-in magic link to:
            </p>
            <p className="font-semibold text-[var(--foreground)]">{email}</p>
          </div>
          <div className="rounded-lg bg-[var(--muted)] p-4 text-xs text-[var(--muted-foreground)] space-y-2">
            <p>1. Click the link in the email to log in automatically.</p>
            <p>2. If you don't see it, please check your **spam or junk folder**.</p>
            <p>3. The link will expire in 24 hours.</p>
          </div>
          <button
            onClick={() => {
              setIsSuccess(false);
              setEmail("");
            }}
            className="w-full rounded-lg border border-[var(--border)] py-2 text-sm font-medium hover:bg-[var(--muted)] transition-colors"
          >
            Back to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-[80vh] flex-col items-center justify-center overflow-hidden px-4 py-12 sm:px-6 lg:px-8">
      {/* Decorative dynamic background blobs */}
      <div className="absolute top-1/4 left-1/4 -z-10 h-72 w-72 rounded-full bg-[var(--primary)]/10 blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 -z-10 h-72 w-72 rounded-full bg-[var(--primary)]/5 blur-3xl" />

      <div className="w-full max-w-md space-y-6">
        {/* Brand header */}
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--primary)]/10 text-[var(--primary)]">
            <MessageCircle className="h-7 w-7" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">WhatsApp Analyzer</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            High-fidelity chat insights and session metrics
          </p>
        </div>

        {/* Auth card */}
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)]/90 p-8 shadow-2xl backdrop-blur-md">
          {/* Custom interactive tabs */}
          <div className="mb-6 flex rounded-lg bg-[var(--muted)] p-1">
            <button
              onClick={() => {
                setActiveTab("login");
                setError(null);
              }}
              className={`flex-1 rounded-md py-1.5 text-center text-sm font-medium transition-all ${
                activeTab === "login"
                  ? "bg-[var(--card)] text-[var(--foreground)] shadow-sm"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => {
                setActiveTab("register");
                setError(null);
              }}
              className={`flex-1 rounded-md py-1.5 text-center text-sm font-medium transition-all ${
                activeTab === "register"
                  ? "bg-[var(--card)] text-[var(--foreground)] shadow-sm"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              Register
            </button>
          </div>

          {/* Dynamic copywriting based on tab */}
          <div className="mb-6 text-center space-y-1">
            <h2 className="text-xl font-semibold">
              {activeTab === "login" ? "Welcome Back!" : "Create an Account"}
            </h2>
            <p className="text-xs text-[var(--muted-foreground)] px-2">
              {activeTab === "login"
                ? "Enter your email address to receive a secure passwordless login magic link."
                : "Enter your email to sign up. A verification link will be sent to establish your workspace."}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label htmlFor="email" className="text-xs font-medium text-[var(--muted-foreground)]">
                Email Address
              </label>
              <div className="relative flex items-center">
                <span className="absolute left-3 text-[var(--muted-foreground)]">
                  <Mail className="h-4 w-4" />
                </span>
                <input
                  id="email"
                  type="email"
                  required
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  className="w-full rounded-lg border border-[var(--border)] bg-transparent py-2.5 pl-10 pr-4 text-sm outline-none transition-all placeholder:text-[var(--muted-foreground)]/50 focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] disabled:opacity-50"
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-start gap-2 rounded-lg bg-red-500/10 p-3 text-xs text-red-500 border border-red-500/20">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold">Authentication failed: </span>
                  {error}
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !email}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-[var(--primary)] py-2.5 text-sm font-semibold text-[var(--primary-foreground)] shadow-lg shadow-[var(--primary)]/20 hover:opacity-95 transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Sending magic link...
                </>
              ) : (
                <>
                  {activeTab === "login" ? "Sign In" : "Register"}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
