import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    if (!session || !session.user || !session.user.id) {
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
    // This gives us a unique workspace ID that we can pass to FastAPI/Qdrant
    const workspace = await prisma.workspace.create({
      data: {
        userId: session.user.id,
        workspaceName,
        chatData: "", // filled after FastAPI returns
        summary: "",  // filled after FastAPI returns
      },
    });

    // 2. Call the Python FastAPI backend to persist embeddings to Qdrant
    const persistResponse = await fetch(`${BACKEND_URL}/api/v1/workspaces/persist`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: chatId,
        workspace_id: workspace.id,
        workspace_name: workspaceName,
      }),
    });

    if (!persistResponse.ok) {
      // If FastAPI fails, clean up the created PostgreSQL record to prevent orphans
      await prisma.workspace.delete({ where: { id: workspace.id } });
      const errorText = await persistResponse.text();
      return NextResponse.json(
        { error: `FastAPI error: ${errorText}` },
        { status: persistResponse.status }
      );
    }

    const result = await persistResponse.json();

    // 3. Update the PostgreSQL record with the raw chat text and summary returned from the backend
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
  } catch (error: any) {
    console.error("Error creating workspace:", error);
    return NextResponse.json(
      { error: error.message || "Failed to create workspace" },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    const session = await auth();
    if (!session || !session.user || !session.user.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const workspaces = await prisma.workspace.findMany({
      where: {
        userId: session.user.id,
      },
      select: {
        id: true,
        workspaceName: true,
        createdAt: true,
        summary: true,
      },
      orderBy: {
        createdAt: "desc",
      },
    });

    return NextResponse.json({ workspaces });
  } catch (error: any) {
    console.error("Error listing workspaces:", error);
    return NextResponse.json(
      { error: error.message || "Failed to list workspaces" },
      { status: 500 }
    );
  }
}
