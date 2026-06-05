import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "@/lib/auth-verify";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://localhost:8000";

async function proxyRequest(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const pathStr = path.join("/");

  const isPublicPath = pathStr === "auth/register" || pathStr === "auth/verify-otp";

  if (!isPublicPath) {
    const user = await verifyAuth(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
  }
  const url = new URL(req.nextUrl);
  
  const targetUrl = `${BACKEND_URL}/api/v1/${pathStr}${url.search}`;

  let token = req.headers.get("Authorization")?.slice(7) || "";
  if (!token) {
    token = req.nextUrl.searchParams.get("token") || "";
  }
  if (!token) {
    token = req.cookies.get("auth_token")?.value || "";
  }

  const headers = new Headers();
  
  // Forward essential headers
  const headersToForward = ["accept", "accept-language", "content-type", "user-agent", "referer"];
  for (const h of headersToForward) {
    const val = req.headers.get(h);
    if (val) {
      headers.set(h, val);
    }
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  try {
    let body: ArrayBuffer | undefined = undefined;
    if (req.method !== "GET" && req.method !== "HEAD") {
      body = await req.arrayBuffer();
    }

    const res = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
      cache: "no-store",
    });

    const data = await res.arrayBuffer();
    const resHeaders = new Headers();
    
    const headersToReturn = ["content-type", "content-length", "cache-control"];
    for (const h of headersToReturn) {
      const val = res.headers.get(h);
      if (val) {
        resHeaders.set(h, val);
      }
    }

    return new NextResponse(data, {
      status: res.status,
      headers: resHeaders,
    });
  } catch (error: unknown) {
    console.error("Proxy error for target:", targetUrl, error);
    return NextResponse.json({ error: "Failed to connect to backend" }, { status: 502 });
  }
}

export { proxyRequest as GET, proxyRequest as POST, proxyRequest as PUT, proxyRequest as DELETE, proxyRequest as PATCH };
