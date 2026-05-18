import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

interface Context {
  params: Promise<{ id: string }>;
}

export async function GET(req: NextRequest, { params }: Context) {
  try {
    const session = await auth();
    if (!session || !session.user || !session.user.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;

    // 1. Fetch workspace from database and check ownership
    const workspace = await prisma.workspace.findUnique({
      where: { id },
    });

    if (!workspace) {
      return NextResponse.json({ error: "Workspace not found" }, { status: 404 });
    }

    if (workspace.userId !== session.user.id) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    // 2. Retrieve all messages sorted by date ascending
    const messages = await prisma.message.findMany({
      where: { workspaceId: id },
      orderBy: { createdAt: "asc" },
      select: {
        role: true,
        content: true,
      },
    });

    return NextResponse.json({ status: "success", messages });
  } catch (error: any) {
    console.error("Error fetching chat history:", error);
    return NextResponse.json(
      { error: error.message || "Failed to retrieve chat history" },
      { status: 500 }
    );
  }
}

export async function POST(req: NextRequest, { params }: Context) {
  try {
    const session = await auth();
    if (!session || !session.user || !session.user.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;

    // 1. Fetch workspace and verify ownership
    const workspace = await prisma.workspace.findUnique({
      where: { id },
    });

    if (!workspace) {
      return NextResponse.json({ error: "Workspace not found" }, { status: 404 });
    }

    if (workspace.userId !== session.user.id) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    // 2. Parse and validate new message fields
    const body = await req.json();
    const { role, content } = body;

    if (!role || !content) {
      return NextResponse.json(
        { error: "role and content are required fields" },
        { status: 400 }
      );
    }

    if (role !== "user" && role !== "assistant") {
      return NextResponse.json(
        { error: "role must be either 'user' or 'assistant'" },
        { status: 400 }
      );
    }

    // 3. Create persistent message in PostgreSQL
    const message = await prisma.message.create({
      data: {
        workspaceId: id,
        role,
        content,
      },
    });

    return NextResponse.json({ status: "success", message });
  } catch (error: any) {
    console.error("Error saving chat message:", error);
    return NextResponse.json(
      { error: error.message || "Failed to save message" },
      { status: 500 }
    );
  }
}
