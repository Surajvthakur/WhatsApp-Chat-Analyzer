import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

const BACKEND_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Context {
  params: Promise<{ id: string }>;
}

export async function DELETE(req: NextRequest, { params }: Context) {
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

    // 2. Call FastAPI to delete from Qdrant and RAM
    try {
      const deleteResponse = await fetch(`${BACKEND_URL}/api/v1/workspaces/${id}`, {
        method: "DELETE",
      });
      if (!deleteResponse.ok) {
        console.warn(`Failed to delete workspace embeddings from FastAPI for ID ${id}`);
      }
    } catch (apiErr) {
      console.error(`Network error calling FastAPI to delete workspace ${id}:`, apiErr);
    }

    // 3. Delete from PostgreSQL database via Prisma
    await prisma.workspace.delete({
      where: { id },
    });

    return NextResponse.json({ status: "success", message: "Workspace deleted successfully" });
  } catch (error: any) {
    console.error("Error deleting workspace:", error);
    return NextResponse.json(
      { error: error.message || "Failed to delete workspace" },
      { status: 500 }
    );
  }
}
