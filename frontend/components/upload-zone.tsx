"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { FileText, Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

export function UploadZone({ onFileSelect, disabled }: UploadZoneProps) {
  const [fileName, setFileName] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[]) => {
      const file = accepted[0];
      if (!file) return;
      setFileName(file.name);
      onFileSelect(file);
    },
    [onFileSelect],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/plain": [".txt"] },
    maxFiles: 1,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-8 py-16 transition-colors",
        isDragActive
          ? "border-[var(--primary)] bg-[var(--primary)]/5"
          : "border-[var(--border)] hover:border-[var(--primary)]/50 hover:bg-[var(--muted)]/50",
        disabled && "pointer-events-none opacity-50",
      )}
    >
      <input {...getInputProps()} />
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--primary)]/10">
        {fileName ? (
          <FileText className="h-7 w-7 text-[var(--primary)]" />
        ) : (
          <Upload className="h-7 w-7 text-[var(--primary)]" />
        )}
      </div>
      <p className="text-center text-lg font-medium">
        {isDragActive ? "Drop your chat file here" : "Drag & drop your WhatsApp export"}
      </p>
      <p className="mt-2 text-center text-sm text-[var(--muted-foreground)]">
        or click to browse — .txt files only
      </p>
      {fileName && (
        <p className="mt-4 rounded-full bg-[var(--muted)] px-4 py-1 text-sm font-medium">
          {fileName}
        </p>
      )}
    </div>
  );
}
