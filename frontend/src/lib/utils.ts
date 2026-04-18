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
  if (p >= 0.85) return "text-success";
  if (p >= 0.6) return "text-warning";
  return "text-danger";
}

export function masteryBg(p: number): string {
  if (p >= 0.85) return "bg-success";
  if (p >= 0.6) return "bg-warning";
  return "bg-danger";
}

export function difficultyLabel(level: number): string {
  const labels: Record<number, string> = { 1: "Dễ", 2: "Trung bình", 3: "Khó" };
  return labels[level] || "Unknown";
}

interface NameSource {
  first_name?: string | null;
  last_name?: string | null;
  username?: string | null;
}

/**
 * Build a display name from a (possibly partial) user object.
 *
 * Order of preference: "Last First" → "First" → "Last" → username → fallback.
 * Avoids "undefined undefined" when the user is null or only has a username.
 */
export function displayName(user: NameSource | null | undefined, fallback = "Bạn"): string {
  if (!user) return fallback;
  const first = (user.first_name || "").trim();
  const last = (user.last_name || "").trim();
  if (last && first) return `${last} ${first}`;
  if (first) return first;
  if (last) return last;
  return user.username?.trim() || fallback;
}
