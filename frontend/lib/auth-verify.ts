import { NextRequest } from "next/server";
import { jwtVerify } from "jose";

const AUTH_SECRET = process.env.AUTH_SECRET || "";

interface JwtUser {
  id: string;
  email: string;
}

/**
 * Verify the JWT from the Authorization header.
 * Returns the decoded user payload or null if invalid.
 */
export async function verifyAuth(req: NextRequest): Promise<JwtUser | null> {
  let token: string | undefined;

  // 1. Check Authorization header
  const authHeader = req.headers.get("Authorization");
  if (authHeader?.startsWith("Bearer ")) {
    token = authHeader.slice(7);
  }

  // 2. Check token query parameter
  if (!token) {
    token = req.nextUrl.searchParams.get("token") || undefined;
  }

  // 3. Check auth_token cookie
  if (!token) {
    token = req.cookies.get("auth_token")?.value;
  }

  if (!token) return null;

  try {
    const secret = new TextEncoder().encode(AUTH_SECRET);
    const { payload } = await jwtVerify(token, secret, {
      algorithms: ["HS256"],
    });
    return {
      id: payload.sub as string,
      email: payload.email as string,
    };
  } catch {
    return null;
  }
}
