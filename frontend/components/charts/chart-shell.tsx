"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface ChartShellProps {
  title: string;
  description?: string;
  isLoading?: boolean;
  isEmpty?: boolean;
  emptyMessage?: string;
  children: React.ReactNode;
  className?: string;
}

export function ChartShell({
  title,
  description,
  isLoading,
  isEmpty,
  emptyMessage = "No data available",
  children,
  className,
}: ChartShellProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-[280px] w-full" />
        ) : isEmpty ? (
          <div className="flex h-[280px] items-center justify-center text-sm text-[var(--muted-foreground)]">
            {emptyMessage}
          </div>
        ) : (
          <div className="h-[280px] w-full">{children}</div>
        )}
      </CardContent>
    </Card>
  );
}
