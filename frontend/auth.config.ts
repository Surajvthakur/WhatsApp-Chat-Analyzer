import type { NextAuthConfig } from "next-auth"
import Resend from "next-auth/providers/resend"

export const authConfig = {
  providers: [
    Resend({
      from: "onboarding@resend.dev"
    })
  ],
  pages: {
    signIn: "/login",
  },
  session: { strategy: "jwt" },
  trustHost: true
} satisfies NextAuthConfig
