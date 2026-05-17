import NextAuth from "next-auth"
import { authConfig } from "./auth.config"

const { auth } = NextAuth(authConfig)

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const { pathname } = req.nextUrl;
  
  const isProtectedRoute = pathname.startsWith('/dashboard') || 
                           pathname.startsWith('/workspaces') || 
                           pathname.startsWith('/profile');
                           
  if (isProtectedRoute && !isLoggedIn) {
    const newUrl = new URL("/api/auth/signin", req.nextUrl.origin);
    return Response.redirect(newUrl);
  }
})

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
