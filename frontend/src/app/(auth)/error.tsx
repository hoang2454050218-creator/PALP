"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AuthError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="text-center max-w-md" role="alert">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Không thể tải trang đăng nhập</h2>
        <p className="text-sm text-muted-foreground mb-6">
          Vui lòng kiểm tra kết nối mạng và thử lại.
        </p>
        <Button onClick={reset}>
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          Thử lại
        </Button>
      </div>
    </div>
  );
}
