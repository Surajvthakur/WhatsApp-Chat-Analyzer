import { NextRequest, NextResponse } from "next/server";
import { verifyAuth } from "@/lib/auth-verify";
import { prisma } from "@/lib/prisma";


const BACKEND_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Context {
  params: Promise<{ id: string }>;
}

export async function DELETE(req: NextRequest, { params }: Context) {
  try {
    const user = await verifyAuth(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;

    const workspace = await prisma.workspace.findUnique({
      where: { id },
    });

    if (!workspace) {
      return NextResponse.json({ error: "Workspace not found" }, { status: 404 });
    }

    if (workspace.userId !== user.id) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    // Delete from Qdrant and RAM via FastAPI
    try {
      const token = req.headers.get("Authorization")?.slice(7) || "";
      const deleteResponse = await fetch(`${BACKEND_URL}/api/v1/workspaces/${id}`, {
        method: "DELETE",
        headers: token ? { "Authorization": `Bearer ${token}` } : {},
      });
      if (!deleteResponse.ok) {
        console.warn(`Failed to delete workspace embeddings from FastAPI for ID ${id}`);
      }
    } catch (apiErr) {
      console.error(`Network error calling FastAPI to delete workspace ${id}:`, apiErr);
    }

    await prisma.workspace.delete({ where: { id } });

    return NextResponse.json({ status: "success", message: "Workspace deleted successfully" });
  } catch (error: unknown) {
    console.error("Error deleting workspace:", error);
    const message = error instanceof Error ? error.message : "Failed to delete workspace";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function GET(req: NextRequest, { params }: Context) {
  try {
    const user = await verifyAuth(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { id } = await params;

    const workspace = await prisma.workspace.findUnique({
      where: { id },
    });

    if (!workspace) {
      return NextResponse.json({ saved: false });
    }

    if (workspace.userId !== user.id) {
      return NextResponse.json({ error: "Forbidden" }, { status: 403 });
    }

    return NextResponse.json({ saved: true, workspaceName: workspace.workspaceName });
  } catch (error: unknown) {
    console.error("Error checking workspace:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}

