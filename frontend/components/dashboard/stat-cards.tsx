"use client";

import { useQuery } from "@tanstack/react-query";
import { Link2, MessageSquare, Image, Type } from "lucide-react";
import { getStats } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceStore } from "@/lib/workspace-store";

const stats = [
  { key: "messages" as const, label: "Total Messages", icon: MessageSquare },
  { key: "words" as const, label: "Total Words", icon: Type },
  { key: "media" as const, label: "Media Shared", icon: Image },
  { key: "links" as const, label: "Links Shared", icon: Link2 },
];

export function StatCards() {
  const { chatId, selectedUser } = useWorkspaceStore();
  const { data, isLoading } = useQuery({
    queryKey: ["stats", chatId, selectedUser],
    queryFn: () => getStats(chatId, selectedUser),
  });

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map(({ key, label, icon: Icon }) => (
        <Card key={key}>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[var(--primary)]/10">
              <Icon className="h-6 w-6 text-[var(--primary)]" />
            </div>
            <div>
              <p className="text-sm text-[var(--muted-foreground)]">{label}</p>
              {isLoading ? (
                <Skeleton className="mt-1 h-8 w-16" />
              ) : (
                <p className="text-2xl font-bold tabular-nums">
                  {data?.[key]?.toLocaleString() ?? "—"}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
