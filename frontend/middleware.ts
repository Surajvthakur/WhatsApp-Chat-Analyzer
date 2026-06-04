import { NextResponse, type NextRequest } from "next/server";

/**
 * Lightweight edge middleware — protects server-rendered routes by checking
 * for the presence of a JWT cookie. Actual token validation happens on the
 * FastAPI backend; this is just a navigation guard.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isProtectedRoute =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/workspaces") ||
    pathname.startsWith("/profile");

  if (isProtectedRoute) {
    const token = request.cookies.get("auth_token")?.value;
    if (!token) {
      const loginUrl = new URL("/login", request.nextUrl.origin);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
