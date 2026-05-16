import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

export function monthLabel(month: number | string): string {
  const n = typeof month === "string" ? parseInt(month, 10) : month;
  if (Number.isNaN(n) || n < 1 || n > 12) return String(month);
  return MONTH_NAMES[n - 1];
}
