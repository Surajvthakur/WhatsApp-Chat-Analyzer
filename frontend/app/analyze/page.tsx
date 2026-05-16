"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { UploadZone } from "@/components/upload-zone";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError, uploadChat } from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function AnalyzePage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
    </div>
  );
}
