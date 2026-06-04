"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { UploadZone } from "@/components/upload-zone";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { 
  ApiError, 
  uploadChat, 
  getWorkspaces, 
  loadWorkspace, 
  deleteWorkspace, 
  Workspace 
} from "@/lib/api";
import { Loader2, Database, Trash2, ArrowRight } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export default function AnalyzePage() {
  const { user } = useAuth();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [loadingWorkspaceId, setLoadingWorkspaceId] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      fetchWorkspaces();
    }
  }, [user]);

  async function fetchWorkspaces() {
    setLoadingWorkspaces(true);
    try {
      const list = await getWorkspaces();
      setWorkspaces(list);
    } catch (err) {
      console.error("Failed to load workspaces", err);
    } finally {
      setLoadingWorkspaces(false);
    }
  }

  async function handleOpenWorkspace(id: string) {
    setLoadingWorkspaceId(id);
    try {
      await loadWorkspace(id);
      router.push(`/dashboard/${id}`);
    } catch (err: any) {
      setError(err.message || "Failed to load workspace.");
    } finally {
      setLoadingWorkspaceId(null);
    }
  }

  async function handleDeleteWorkspace(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this workspace and all its vector embeddings permanently?")) {
      return;
    }
    try {
      await deleteWorkspace(id);
      setWorkspaces(workspaces.filter((w) => w.id !== id));
    } catch (err: any) {
      setError(err.message || "Failed to delete workspace.");
    }
  }

  async function handleAnalyze() {
    if (!file) {
      setError("Please select a .txt file first.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const result = await uploadChat(file);
      router.push(`/dashboard/${result.chat_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Upload failed. Is the API server running?");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold">Upload your chat</h1>
      <p className="mt-2 text-[var(--muted-foreground)]">
        Export a chat from WhatsApp (without media) as a .txt file and upload
        it here.
      </p>

      <div className="mt-8">
        <UploadZone
          onFileSelect={(f) => {
            setFile(f);
            setError(null);
          }}
          disabled={loading}
        />
      </div>

      {error && (
        <Alert variant="destructive" className="mt-4">
          {error}
        </Alert>
      )}

      <Button
        className="mt-6 w-full"
        size="lg"
        disabled={!file || loading}
        onClick={handleAnalyze}
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Analyzing…
          </>
        ) : (
          "Show analysis"
        )}
      </Button>

      {user && (
        <div className="mt-12 border-t border-[var(--border)] pt-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2 text-[var(--foreground)]">
            <Database className="h-5 w-5 text-[var(--primary)]" />
            Your Saved Workspaces
          </h2>
          
          {loadingWorkspaces ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="h-20 animate-pulse rounded-xl bg-[var(--muted)]" />
              ))}
            </div>
          ) : workspaces.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)] bg-[var(--muted)]/30 rounded-xl p-6 text-center border border-dashed border-[var(--border)]">
              No saved workspaces yet. Upload a chat and click "Save Workspace" to see it here!
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {workspaces.map((w) => (
                <div
                  key={w.id}
                  onClick={() => handleOpenWorkspace(w.id)}
                  className="group relative flex flex-col justify-between rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-sm hover:border-[var(--primary)] hover:shadow-md transition-all cursor-pointer overflow-hidden duration-200"
                >
                  <div className="flex justify-between items-start">
                    <div className="pr-6">
                      <h3 className="font-semibold text-sm text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors line-clamp-1">
                        {w.workspaceName}
                      </h3>
                      <p className="text-[10px] text-[var(--muted-foreground)] mt-1">
                        Saved on {new Date(w.createdAt).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={(e) => handleDeleteWorkspace(w.id, e)}
                      className="absolute top-3 right-3 text-[var(--muted-foreground)] hover:text-red-500 rounded-lg p-1.5 hover:bg-[var(--muted)] transition-all z-10"
                      title="Delete Workspace"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  
                  {w.summary && (
                    <p className="text-xs text-[var(--muted-foreground)] mt-3 line-clamp-2 italic">
                      "{w.summary}"
                    </p>
                  )}
                  
                  <div className="mt-4 flex justify-end">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-xs h-7 gap-1 group-hover:translate-x-1 transition-transform"
                      disabled={loadingWorkspaceId === w.id}
                    >
                      {loadingWorkspaceId === w.id ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Loading…
                        </>
                      ) : (
                        <>
                          Open
                          <ArrowRight className="h-3 w-3" />
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
