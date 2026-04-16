import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function masteryColor(p: number): string {
  if (p >= 0.85) return "text-green-600";
  if (p >= 0.6) return "text-yellow-600";
  return "text-red-600";
}

export function masteryBg(p: number): string {
  if (p >= 0.85) return "bg-green-500";
  if (p >= 0.6) return "bg-yellow-500";
  return "bg-red-500";
}

export function difficultyLabel(level: number): string {
  const labels: Record<number, string> = { 1: "Dễ", 2: "Trung bình", 3: "Khó" };
  return labels[level] || "Unknown";
}
