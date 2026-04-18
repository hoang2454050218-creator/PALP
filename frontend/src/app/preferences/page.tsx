"use client";

import { Type, Palette, Eye, Zap, RotateCcw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { usePreferences, type FontScale, type ThemeMode, type FontFamily } from "@/hooks/use-preferences";
import { cn } from "@/lib/utils";

const FONT_SCALES: Array<{ value: FontScale; label: string; description: string }> = [
  { value: "100", label: "100%", description: "Mặc định" },
  { value: "125", label: "125%", description: "Hơi lớn" },
  { value: "150", label: "150%", description: "Lớn" },
  { value: "200", label: "200%", description: "Rất lớn" },
];

const THEMES: Array<{ value: ThemeMode; label: string; description: string }> = [
  { value: "light", label: "Sáng", description: "Nền trắng, chữ xám đen" },
  { value: "dark", label: "Tối", description: "Nền tối, chữ sáng" },
  { value: "high-contrast", label: "Tương phản cao", description: "WCAG AAA, contrast 7:1+" },
];

const FONTS: Array<{ value: FontFamily; label: string; description: string }> = [
  { value: "default", label: "Mặc định", description: "Inter (sans-serif)" },
  { value: "dyslexic", label: "OpenDyslexic", description: "Dễ đọc cho người khó đọc" },
];

export default function PreferencesPage() {
  const {
    fontScale, theme, fontFamily, reducedMotion,
    setFontScale, setTheme, setFontFamily, setReducedMotion, reset,
  } = usePreferences();

  return (
    <div>
      <PageHeader
        title="Tùy chỉnh giao diện"
        description="Điều chỉnh để học tập thoải mái nhất với bạn. Lưu tự động trong trình duyệt."
      />

      <div className="grid gap-6 max-w-3xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Type className="h-5 w-5 text-primary" aria-hidden="true" />
              Cỡ chữ
            </CardTitle>
            <CardDescription>
              Phóng to chữ và icon để dễ đọc hơn. Áp dụng cho toàn bộ ứng dụng.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div role="radiogroup" aria-label="Chọn cỡ chữ" className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {FONT_SCALES.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={fontScale === opt.value}
                  onClick={() => setFontScale(opt.value)}
                  className={cn(
                    "min-h-[60px] rounded-lg border-2 px-4 py-3 text-sm font-medium transition-all",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    fontScale === opt.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border hover:border-primary/50",
                  )}
                >
                  <div className="text-base font-semibold">{opt.label}</div>
                  <div className="text-xs text-muted-foreground mt-1">{opt.description}</div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Palette className="h-5 w-5 text-primary" aria-hidden="true" />
              Chế độ màu
            </CardTitle>
            <CardDescription>
              Tương phản cao đáp ứng tiêu chuẩn WCAG 2.2 AAA cho người khiếm thị.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div role="radiogroup" aria-label="Chọn chế độ màu" className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {THEMES.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={theme === opt.value}
                  onClick={() => setTheme(opt.value)}
                  className={cn(
                    "min-h-[60px] rounded-lg border-2 px-4 py-3 text-left transition-all",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    theme === opt.value
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-primary/50",
                  )}
                >
                  <div className="font-semibold text-sm">{opt.label}</div>
                  <div className="text-xs text-muted-foreground mt-1">{opt.description}</div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Eye className="h-5 w-5 text-primary" aria-hidden="true" />
              Phông chữ
            </CardTitle>
            <CardDescription>
              OpenDyslexic được thiết kế cho người mắc chứng khó đọc.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div role="radiogroup" aria-label="Chọn phông chữ" className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {FONTS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={fontFamily === opt.value}
                  onClick={() => setFontFamily(opt.value)}
                  className={cn(
                    "min-h-[60px] rounded-lg border-2 px-4 py-3 text-left transition-all",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    fontFamily === opt.value
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-primary/50",
                  )}
                >
                  <div className="font-semibold text-sm">{opt.label}</div>
                  <div className="text-xs text-muted-foreground mt-1">{opt.description}</div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Zap className="h-5 w-5 text-primary" aria-hidden="true" />
              Giảm chuyển động
            </CardTitle>
            <CardDescription>
              Tắt animation nếu bạn cảm thấy mệt mắt hoặc dễ say chuyển động.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <label className="flex items-center justify-between min-h-[44px] cursor-pointer">
              <span className="text-sm">
                Tắt mọi animation và transition trong giao diện
              </span>
              <input
                type="checkbox"
                checked={reducedMotion}
                onChange={(e) => setReducedMotion(e.target.checked)}
                className="h-5 w-5 rounded border-2 border-input cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                aria-label="Bật giảm chuyển động"
              />
            </label>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-4 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Khôi phục cài đặt mặc định
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={reset}
              className="min-h-[44px] gap-2"
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Đặt lại
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
