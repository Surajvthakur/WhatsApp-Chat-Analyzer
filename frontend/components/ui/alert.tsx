import { cn } from "@/lib/utils";

export function Alert({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  variant?: "default" | "destructive";
}) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-lg border px-4 py-3 text-sm",
        variant === "destructive"
          ? "border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-300"
          : "border-[var(--border)] bg-[var(--muted)]",
        className,
      )}
      {...props}
    />
  );
}
