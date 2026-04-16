"use client";

import { AlertTriangle, RefreshCw, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  onBack?: () => void;
}

export function ErrorState({
  title = "Đã xảy ra lỗi",
  message = "Không thể tải dữ liệu. Vui lòng thử lại sau hoặc kiểm tra kết nối mạng.",
  onRetry,
  onBack,
}: ErrorStateProps) {
  return (
    <Card>
      <CardContent className="py-12">
        <div className="flex flex-col items-center text-center" role="alert">
          <div className="rounded-full bg-destructive/10 p-4 mb-4">
            <AlertTriangle className="h-8 w-8 text-destructive" aria-hidden="true" />
          </div>
          <h3 className="text-lg font-semibold mb-2">{title}</h3>
          <p className="text-sm text-muted-foreground max-w-md mb-6">{message}</p>
          <div className="flex items-center gap-3">
            {onBack && (
              <Button variant="outline" onClick={onBack}>
                <ArrowLeft className="mr-2 h-4 w-4" aria-hidden="true" />
                Quay lại
              </Button>
            )}
            {onRetry && (
              <Button onClick={onRetry}>
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                Thử lại
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
