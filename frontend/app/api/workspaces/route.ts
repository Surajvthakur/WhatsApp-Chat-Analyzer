import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "@/lib/auth-verify";
import { prisma } from "@/lib/prisma";

const BACKEND_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const user = await verifyAuth(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { chatId, workspaceName } = body;

    if (!chatId || !workspaceName) {
      return NextResponse.json(
        { error: "chatId and workspaceName are required" },
        { status: 400 }
      );
    }

    // 1. Create a draft Workspace in PostgreSQL first
    const workspace = await prisma.workspace.create({
      data: {
        userId: user.id,
        workspaceName,
        chatData: "",
        summary: "",
      },
    });

    // 2. Call the Python FastAPI backend to persist embeddings to Qdrant
    const token = req.headers.get("Authorization")?.slice(7) || "";
    const persistResponse = await fetch(`${BACKEND_URL}/api/v1/workspaces/persist`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        chat_id: chatId,
        workspace_id: workspace.id,
        workspace_name: workspaceName,
      }),
    });

    if (!persistResponse.ok) {
      await prisma.workspace.delete({ where: { id: workspace.id } });
      const errorText = await persistResponse.text();
      return NextResponse.json(
        { error: `FastAPI error: ${errorText}` },
        { status: persistResponse.status }
      );
    }

    const result = await persistResponse.json();

    // 3. Update the PostgreSQL record with the raw chat text and summary
    const finalWorkspace = await prisma.workspace.update({
      where: { id: workspace.id },
      data: {
        chatData: result.raw_text,
        summary: result.summary,
      },
    });

    return NextResponse.json({
      status: "success",
      workspace: {
        id: finalWorkspace.id,
        workspaceName: finalWorkspace.workspaceName,
        createdAt: finalWorkspace.createdAt,
        summary: finalWorkspace.summary,
      },
    });
  } catch (error: unknown) {
    console.error("Error creating workspace:", error);
    const message = error instanceof Error ? error.message : "Failed to create workspace";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  try {
    const user = await verifyAuth(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const workspaces = await prisma.workspace.findMany({
      where: { userId: user.id },
      select: {
        id: true,
        workspaceName: true,
        createdAt: true,
        summary: true,
      },
      orderBy: { createdAt: "desc" },
    });

    return NextResponse.json({ workspaces });
  } catch (error: unknown) {
    console.error("Error listing workspaces:", error);
    const message = error instanceof Error ? error.message : "Failed to list workspaces";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
