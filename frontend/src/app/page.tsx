"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, getStoredUser } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    const user = getStoredUser();
    if (user?.role === "lecturer") {
      router.replace("/overview");
    } else {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center bg-background" role="status" aria-label="Đang chuyển hướng">
      <div className="flex flex-col items-center gap-4">
        <div className="h-10 w-10 motion-safe:animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-sm text-muted-foreground motion-safe:animate-pulse">Đang tải...</p>
      </div>
    </div>
  );
}
