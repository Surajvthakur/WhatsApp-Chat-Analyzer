import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Context {
  params: Promise<{ id: string }>;
}

export async function POST(req: NextRequest, { params }: Context) {
  try {
    const session = await auth();
    if (!session || !session.user || !session.user.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;

    // 1. Fetch workspace from database
    const workspace = await prisma.workspace.findUnique({
      where: { id },
    });

    if (!workspace) {
      return NextResponse.json({ error: "Workspace not found" }, { status: 404 });
    }

    // 2. Check ownership
    if (workspace.userId !== session.user.id) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    // 3. Post to FastAPI backend to restore the chat data in RAM
    const loadResponse = await fetch(`${BACKEND_URL}/api/v1/workspaces/${id}/load`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        raw_text: workspace.chatData,
      }),
    });

    if (!loadResponse.ok) {
      const errorText = await loadResponse.text();
      return NextResponse.json(
        { error: `FastAPI error: ${errorText}` },
        { status: loadResponse.status }
      );
    }

    const result = await loadResponse.json();

    // 4. Return success and the loaded workspace stats
    return NextResponse.json({
      status: "success",
      chatId: result.chat_id,
      users: result.users,
      messageCount: result.message_count,
      dateRange: result.date_range,
    });
  } catch (error: any) {
    console.error("Error loading workspace into RAM:", error);
    return NextResponse.json(
      { error: error.message || "Failed to load workspace" },
      { status: 500 }
    );
  }
}
