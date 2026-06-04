"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Mail,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  MessageCircle,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

type Step = "email" | "otp";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [otpDigits, setOtpDigits] = useState<string[]>(Array(6).fill(""));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Auto-focus first OTP input when step changes
  useEffect(() => {
    if (step === "otp") {
      inputRefs.current[0]?.focus();
    }
  }, [step]);

  // ── Register (send OTP) ──────────────────────────────────────────────────

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail || "Registration failed");
      }

      setStep("otp");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Verify OTP ───────────────────────────────────────────────────────────

  const handleVerifyOtp = async (code?: string) => {
    const otpCode = code || otpDigits.join("");
    if (otpCode.length !== 6) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code: otpCode }),
      });

      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail || "Verification failed");
      }

      const data = await res.json();
      login(data.access_token);
      setIsSuccess(true);

      setTimeout(() => router.push("/analyze"), 1200);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Verification failed";
      setError(message);
      setOtpDigits(Array(6).fill(""));
      inputRefs.current[0]?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  // ── OTP input handlers ───────────────────────────────────────────────────

  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;

    const newDigits = [...otpDigits];
    newDigits[index] = value.slice(-1);
    setOtpDigits(newDigits);

    // Auto-advance to next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all 6 digits are filled
    const fullCode = newDigits.join("");
    if (fullCode.length === 6) {
      handleVerifyOtp(fullCode);
    }
  };

  const handleOtpKeyDown = (
    index: number,
    e: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleOtpPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;
    const newDigits = Array(6).fill("");
    pasted.split("").forEach((ch, i) => (newDigits[i] = ch));
    setOtpDigits(newDigits);
    if (pasted.length === 6) handleVerifyOtp(pasted);
  };

  // ── Success screen ───────────────────────────────────────────────────────

  if (isSuccess) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-6 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-8 text-center shadow-2xl backdrop-blur-md">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--primary)]/10 text-[var(--primary)]">
            <CheckCircle2 className="h-10 w-10 animate-bounce" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold tracking-tight">
              You&apos;re verified!
            </h2>
            <p className="text-sm text-[var(--muted-foreground)]">
              Redirecting you to the dashboard…
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── Main UI ───────────────────────────────────────────────────────────────

  return (
    <div className="relative flex min-h-[80vh] flex-col items-center justify-center overflow-hidden px-4 py-12 sm:px-6 lg:px-8">
      {/* Background blobs */}
      <div className="absolute top-1/4 left-1/4 -z-10 h-72 w-72 rounded-full bg-[var(--primary)]/10 blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 -z-10 h-72 w-72 rounded-full bg-[var(--primary)]/5 blur-3xl" />

      <div className="w-full max-w-md space-y-6">
        {/* Brand header */}
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[var(--primary)]/10 text-[var(--primary)]">
            <MessageCircle className="h-7 w-7" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">
            WhatsApp Analyzer
          </h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            High-fidelity chat insights and session metrics
          </p>
        </div>

        {/* Auth card */}
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)]/90 p-8 shadow-2xl backdrop-blur-md">
          {step === "email" ? (
            <>
              <div className="mb-6 text-center space-y-1">
                <h2 className="text-xl font-semibold">Get Started</h2>
                <p className="text-xs text-[var(--muted-foreground)] px-2">
                  Enter your email to receive a 6-digit verification code.
                </p>
              </div>

              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-1">
                  <label
                    htmlFor="email"
                    className="text-xs font-medium text-[var(--muted-foreground)]"
                  >
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

                {error && (
                  <div className="flex items-start gap-2 rounded-lg bg-red-500/10 p-3 text-xs text-red-500 border border-red-500/20">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isLoading || !email}
                  className="w-full flex items-center justify-center gap-2 rounded-lg bg-[var(--primary)] py-2.5 text-sm font-semibold text-[var(--primary-foreground)] shadow-lg shadow-[var(--primary)]/20 hover:opacity-95 transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Sending code…
                    </>
                  ) : (
                    <>
                      Send Verification Code
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </form>
            </>
          ) : (
            <>
              <div className="mb-6 text-center space-y-1">
                <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-[var(--primary)]/10 text-[var(--primary)]">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <h2 className="text-xl font-semibold">Enter Verification Code</h2>
                <p className="text-xs text-[var(--muted-foreground)] px-2">
                  We sent a 6-digit code to{" "}
                  <span className="font-semibold text-[var(--foreground)]">
                    {email}
                  </span>
                </p>
              </div>

              <div className="space-y-4">
                {/* OTP digit inputs */}
                <div
                  className="flex justify-center gap-2"
                  onPaste={handleOtpPaste}
                >
                  {otpDigits.map((digit, i) => (
                    <input
                      key={i}
                      ref={(el) => {
                        inputRefs.current[i] = el;
                      }}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleOtpChange(i, e.target.value)}
                      onKeyDown={(e) => handleOtpKeyDown(i, e)}
                      disabled={isLoading}
                      className="h-12 w-12 rounded-lg border border-[var(--border)] bg-transparent text-center text-xl font-bold outline-none transition-all focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)] disabled:opacity-50"
                    />
                  ))}
                </div>

                {error && (
                  <div className="flex items-start gap-2 rounded-lg bg-red-500/10 p-3 text-xs text-red-500 border border-red-500/20">
                    <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <div className="text-center text-xs text-[var(--muted-foreground)] space-y-2">
                  <p>Code expires in 5 minutes.</p>
                  <button
                    type="button"
                    onClick={() => {
                      setStep("email");
                      setError(null);
                      setOtpDigits(Array(6).fill(""));
                    }}
                    className="text-[var(--primary)] hover:underline font-medium"
                  >
                    ← Use a different email
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
