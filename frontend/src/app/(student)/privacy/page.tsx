"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Shield, Download, Trash2, FileText,
  CheckCircle, XCircle, Clock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { ErrorState } from "@/components/shared/error-state";
import { CardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";
import type {
  ConsentStatus,
  AuditLogEntry,
  DeletionRequest,
  DataExportResponse,
} from "@/types";
import { ResearchParticipationCard } from "@/components/phase7/research-participation-card";

const TIER_LABELS: Record<string, string> = {
  pii: "Thông tin cá nhân (PII)",
  academic: "Dữ liệu học vụ",
  behavioral: "Dữ liệu hành vi",
  inference: "Dữ liệu suy luận",
};

export default function PrivacyCenterPage() {
  const [consents, setConsents] = useState<ConsentStatus[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [deletionRequests, setDeletionRequests] = useState<DeletionRequest[]>([]);
  const [exporting, setExporting] = useState(false);
  const [deleteTier, setDeleteTier] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  async function loadData() {
    setLoading(true);
    setError(false);
    try {
      const [c, a, d] = await Promise.all([
        api.get<ConsentStatus[]>("/privacy/consent/"),
        api.get<AuditLogEntry[]>("/privacy/audit-log/"),
        api.get<DeletionRequest[]>("/privacy/delete/requests/"),
      ]);
      setConsents(Array.isArray(c) ? c : (c as any).results ?? []);
      setAuditLog(Array.isArray(a) ? a : (a as any).results ?? []);
      setDeletionRequests(Array.isArray(d) ? d : (d as any).results ?? []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function toggleConsent(purpose: string, granted: boolean) {
    try {
      const result = await api.post<ConsentStatus[]>("/privacy/consent/", {
        consents: [{ purpose, granted }],
        version: "1.0",
      });
      setConsents(Array.isArray(result) ? result : (result as any).results ?? []);
      toast({
        variant: "success",
        title: granted ? "Đã đồng ý" : "Đã thu hồi",
        description: `Quyết định đồng thuận đã được cập nhật.`,
      });
    } catch {
      toast({ variant: "error", title: "Không thể cập nhật", description: "Vui lòng thử lại sau." });
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const data = await api.get<DataExportResponse>("/privacy/export/");
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `palp-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ variant: "success", title: "Đã xuất dữ liệu", description: "File đã được tải về máy." });
      loadData();
    } catch {
      toast({ variant: "error", title: "Không thể xuất dữ liệu", description: "Vui lòng thử lại sau." });
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    if (!deleteTier) return;
    try {
      await api.post("/privacy/delete/", {
        tiers: [deleteTier],
        confirm: true,
      });
      toast({ variant: "success", title: "Yêu cầu xóa đã được ghi nhận", description: "Dữ liệu sẽ được xử lý theo quy trình." });
      setDeleteTier(null);
      setDeleteConfirm(false);
      loadData();
    } catch {
      toast({ variant: "error", title: "Không thể xóa dữ liệu", description: "Vui lòng thử lại sau." });
    }
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Quyền riêng tư" />
        <ErrorState
          title="Không thể tải dữ liệu"
          message="Vui lòng kiểm tra kết nối mạng và thử lại."
          onRetry={loadData}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <PageHeader title="Quyền riêng tư" description="Quản lý đồng thuận, xuất và xóa dữ liệu cá nhân" />
        <div className="grid gap-6 lg:grid-cols-2">
          <CardSkeleton lines={5} />
          <div className="space-y-6">
            <CardSkeleton lines={2} />
            <CardSkeleton lines={3} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Quyền riêng tư"
        description="Quản lý đồng thuận, xuất và xóa dữ liệu cá nhân"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="h-5 w-5" aria-hidden="true" />
              Đồng thuận thu thập dữ liệu
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {consents.map((consent) => (
              <div key={consent.purpose} className="rounded-lg border p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-sm">{consent.label}</p>
                      {consent.granted ? (
                        <Badge variant="success">
                          <CheckCircle className="h-3 w-3 mr-1" aria-hidden="true" />
                          Đã đồng ý
                        </Badge>
                      ) : (
                        <Badge variant="secondary">
                          <XCircle className="h-3 w-3 mr-1" aria-hidden="true" />
                          Từ chối
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {consent.description}
                    </p>
                    {consent.last_changed_at && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Cập nhật: {new Date(consent.last_changed_at).toLocaleString("vi-VN")}
                      </p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant={consent.granted ? "destructive" : "default"}
                    onClick={() => toggleConsent(consent.purpose, !consent.granted)}
                  >
                    {consent.granted ? "Thu hồi" : "Đồng ý"}
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Download className="h-5 w-5" aria-hidden="true" />
                Xuất dữ liệu
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Tải về toàn bộ dữ liệu cá nhân dưới dạng JSON,
                bao gồm giải thích từng trường dữ liệu và timestamp.
              </p>
              <Button
                onClick={handleExport}
                disabled={exporting}
                className="w-full"
              >
                <FileText className="h-4 w-4 mr-2" aria-hidden="true" />
                {exporting ? "Đang xuất..." : "Xuất dữ liệu (JSON)"}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Trash2 className="h-5 w-5" aria-hidden="true" />
                Xóa dữ liệu
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Chọn loại dữ liệu muốn xóa. Dữ liệu hành vi và suy luận sẽ bị xóa
                vĩnh viễn. Dữ liệu học vụ sẽ được ẩn danh hóa.
              </p>
              {["behavioral", "inference", "academic", "pii"].map((tier) => (
                <div key={tier} className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="text-sm font-medium">{TIER_LABELS[tier]}</p>
                    <p className="text-xs text-muted-foreground">
                      {tier === "pii" || tier === "academic"
                        ? "Ẩn danh hóa"
                        : "Xóa vĩnh viễn"}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => {
                      setDeleteTier(tier);
                      setDeleteConfirm(false);
                    }}
                  >
                    Xóa
                  </Button>
                </div>
              ))}

              {deletionRequests.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-muted-foreground mb-2">
                    Lịch sử yêu cầu xóa
                  </p>
                  {deletionRequests.slice(0, 5).map((req) => (
                    <div key={req.id} className="flex items-center gap-2 text-xs py-1">
                      <Badge variant={req.status === "completed" ? "success" : "warning"} className="text-[10px]">
                        {req.status}
                      </Badge>
                      <span>{req.tiers.join(", ")}</span>
                      <span className="text-muted-foreground">
                        {new Date(req.requested_at).toLocaleString("vi-VN")}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <ResearchParticipationCard />

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Clock className="h-5 w-5" aria-hidden="true" />
            Nhật ký truy cập dữ liệu
          </CardTitle>
        </CardHeader>
        <CardContent>
          {auditLog.length > 0 ? (
            <div className="space-y-2">
              {auditLog.map((entry) => (
                <div
                  key={entry.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm"
                >
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="text-xs">
                      {entry.action}
                    </Badge>
                    <span>{entry.resource}</span>
                    {entry.actor_username && (
                      <span className="text-muted-foreground">
                        bởi {entry.actor_username}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(entry.created_at).toLocaleString("vi-VN")}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-4 text-muted-foreground text-sm">
              Chưa có nhật ký truy cập
            </p>
          )}
        </CardContent>
      </Card>

      <Dialog.Root open={!!deleteTier} onOpenChange={(open) => { if (!open) { setDeleteTier(null); setDeleteConfirm(false); } }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
          <Dialog.Content
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 p-4"
            aria-describedby="delete-description"
          >
            <Card>
              <CardHeader>
                <Dialog.Title asChild>
                  <CardTitle className="text-lg">Xác nhận xóa dữ liệu</CardTitle>
                </Dialog.Title>
              </CardHeader>
              <CardContent className="space-y-4">
                <Dialog.Description id="delete-description" className="text-sm">
                  Bạn sắp xóa dữ liệu{" "}
                  <span className="font-semibold">{deleteTier ? TIER_LABELS[deleteTier] : ""}</span>.
                  {deleteTier === "pii" || deleteTier === "academic"
                    ? " Dữ liệu sẽ được ẩn danh hóa và không thể khôi phục."
                    : " Dữ liệu sẽ bị xóa vĩnh viễn và không thể khôi phục."}
                </Dialog.Description>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={deleteConfirm}
                    onChange={(e) => setDeleteConfirm(e.target.checked)}
                    className="rounded border-input"
                  />
                  Tôi hiểu và muốn tiếp tục
                </label>
                <div className="flex gap-2">
                  <Dialog.Close asChild>
                    <Button variant="outline" className="flex-1">
                      Hủy
                    </Button>
                  </Dialog.Close>
                  <Button
                    variant="destructive"
                    className="flex-1"
                    disabled={!deleteConfirm}
                    onClick={handleDelete}
                  >
                    Xác nhận xóa
                  </Button>
                </div>
              </CardContent>
            </Card>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
