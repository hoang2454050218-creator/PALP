"use client";

import { useEffect, useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Shield } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import type { ConsentStatus } from "@/types";

interface ConsentModalProps {
  onComplete: () => void;
}

export function ConsentModal({ onComplete }: ConsentModalProps) {
  const { checkConsent } = useAuth();
  const [consents, setConsents] = useState<ConsentStatus[]>([]);
  const [decisions, setDecisions] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<ConsentStatus[]>("/privacy/consent/")
      .then((data) => {
        const list = Array.isArray(data) ? data : (data as any).results ?? [];
        setConsents(list);
        const initial: Record<string, boolean> = {};
        list.forEach((c: ConsentStatus) => {
          initial[c.purpose] = c.granted;
        });
        setDecisions(initial);
      })
      .catch(() => setError("Không thể tải thông tin đồng thuận. Vui lòng tải lại trang."));
  }, []);

  const allDecided = consents.length > 0 && consents.every((c) => c.purpose in decisions);
  const decidedCount = useMemo(
    () => consents.reduce((n, c) => n + (c.purpose in decisions ? 1 : 0), 0),
    [consents, decisions],
  );
  const totalCount = consents.length;
  const declinedCount = useMemo(
    () => Object.values(decisions).filter((v) => v === false).length,
    [decisions],
  );

  async function handleSubmit() {
    if (!allDecided) return;
    setSubmitting(true);
    setError("");

    try {
      await api.post("/privacy/consent/", {
        consents: Object.entries(decisions).map(([purpose, granted]) => ({
          purpose,
          granted,
        })),
      });
      // Force a fresh check so the auth store reflects the new state
      // immediately and the modal does not reappear on next navigation.
      await checkConsent(true);
      onComplete();
    } catch {
      setError("Có lỗi khi lưu. Vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog.Root open modal>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 p-4 max-h-[92vh]"
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          aria-describedby="consent-description"
        >
          <Card className="flex max-h-[92vh] flex-col">
            <CardHeader className="shrink-0">
              <Dialog.Title asChild>
                <CardTitle className="text-xl flex items-center gap-2">
                  <Shield className="h-5 w-5" aria-hidden="true" />
                  Đồng thuận thu thập dữ liệu
                </CardTitle>
              </Dialog.Title>
              <Dialog.Description id="consent-description" className="text-sm text-muted-foreground mt-1">
                Vui lòng xem xét và quyết định cho từng loại dữ liệu bên dưới.
                Bạn có thể thay đổi bất cứ lúc nào tại trang Quyền riêng tư.
              </Dialog.Description>
            </CardHeader>
            <CardContent className="flex flex-1 min-h-0 flex-col gap-4 p-0">
              <div className="flex-1 min-h-0 overflow-y-auto px-6 space-y-4">
                {consents.map((consent) => (
                  <fieldset key={consent.purpose} className="rounded-lg border p-4 space-y-3">
                    <legend className="sr-only">{consent.label}</legend>
                    <div>
                      <p className="font-medium text-sm">{consent.label}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {consent.description}
                      </p>
                    </div>
                    <div className="flex gap-2" role="group" aria-label={`Quyết định cho ${consent.label}`}>
                      <Button
                        size="sm"
                        variant={decisions[consent.purpose] === true ? "default" : "outline"}
                        onClick={() => setDecisions({ ...decisions, [consent.purpose]: true })}
                        aria-pressed={decisions[consent.purpose] === true}
                      >
                        Đồng ý
                      </Button>
                      <Button
                        size="sm"
                        variant={decisions[consent.purpose] === false ? "destructive" : "outline"}
                        onClick={() => setDecisions({ ...decisions, [consent.purpose]: false })}
                        aria-pressed={decisions[consent.purpose] === false}
                      >
                        Từ chối
                      </Button>
                    </div>
                  </fieldset>
                ))}
              </div>

              <div className="shrink-0 space-y-3 border-t bg-card px-6 pb-6 pt-4">
                {error && (
                  <p className="text-sm text-destructive" role="alert">{error}</p>
                )}

                {!allDecided && consents.length > 0 && (
                  <p className="text-xs text-muted-foreground" role="status" aria-live="polite">
                    Bạn đã quyết định {decidedCount}/{totalCount}. Hãy chọn cho từng mục để tiếp tục.
                  </p>
                )}
                {allDecided && declinedCount > 0 && (
                  <p className="text-xs text-warning-foreground" role="status" aria-live="polite">
                    Lưu ý: bạn từ chối {declinedCount} mục. Một số tính năng cá nhân hóa
                    sẽ bị hạn chế. Bạn có thể bật lại bất cứ lúc nào tại trang Quyền riêng tư.
                  </p>
                )}

                <Button
                  className="w-full"
                  onClick={handleSubmit}
                  disabled={!allDecided || submitting}
                >
                  {submitting ? "Đang lưu..." : "Xác nhận & Tiếp tục"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
