"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ChartShellProps {
  title: string;
  description?: string;
  isLoading?: boolean;
  isEmpty?: boolean;
  emptyMessage?: string;
  children: React.ReactNode;
  className?: string;
  /** Override the default fixed chart height (e.g. `h-auto` for tall tables). */
  contentClassName?: string;
}

export function ChartShell({
  title,
  description,
  isLoading,
  isEmpty,
  emptyMessage = "No data available",
  children,
  className,
  contentClassName,
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
          <div className={cn("h-[280px] w-full", contentClassName)}>
            {children}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
