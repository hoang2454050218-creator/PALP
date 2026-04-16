"use client";

import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function LecturerError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <div className="text-center max-w-md" role="alert">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Đã xảy ra lỗi</h2>
        <p className="text-sm text-muted-foreground mb-6">
          Trang không thể tải được. Bạn có thể thử lại hoặc quay về tổng quan lớp.
          Nếu lỗi vẫn tiếp tục, vui lòng liên hệ quản trị viên.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/overview">
            <Button variant="outline">
              <Home className="mr-2 h-4 w-4" aria-hidden="true" />
              Tổng quan lớp
            </Button>
          </Link>
          <Button onClick={reset}>
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            Thử lại
          </Button>
        </div>
      </div>
    </div>
  );
}
