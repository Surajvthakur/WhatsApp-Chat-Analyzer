import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "@/lib/auth-verify";
import { prisma } from "@/lib/prisma";

const BACKEND_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Context {
  params: Promise<{ id: string }>;
}

export async function POST(req: NextRequest, { params }: Context) {
  try {
    const user = await verifyAuth(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;

    const workspace = await prisma.workspace.findUnique({
      where: { id },
      select: { id: true, userId: true },
    });

    if (!workspace) {
      return NextResponse.json({ error: "Workspace not found" }, { status: 404 });
    }

    if (workspace.userId !== user.id) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    // Post to FastAPI backend to restore the chat data in RAM
    const token = req.headers.get("Authorization")?.slice(7) || "";
    const loadResponse = await fetch(`${BACKEND_URL}/api/v1/workspaces/${id}/load`, {
      method: "POST",
      headers: {
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      },
    });

    if (!loadResponse.ok) {
      const errorText = await loadResponse.text();
      return NextResponse.json(
        { error: `FastAPI error: ${errorText}` },
        { status: loadResponse.status }
      );
    }

    const result = await loadResponse.json();

    return NextResponse.json({
      status: "success",
      chatId: result.chat_id,
      users: result.users,
      messageCount: result.message_count,
      dateRange: result.date_range,
    });
  } catch (error: unknown) {
    console.error("Error loading workspace into RAM:", error);
    const message = error instanceof Error ? error.message : "Failed to load workspace";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
