"use client";

import * as React from "react";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { cva } from "class-variance-authority";
import { X, CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

const toastVariants = cva(
  "group pointer-events-auto relative flex w-full items-start gap-3 overflow-hidden rounded-lg border p-4 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full",
  {
    variants: {
      variant: {
        success: "border-green-200 bg-green-50 text-green-900",
        error: "border-red-200 bg-red-50 text-red-900",
        warning: "border-yellow-200 bg-yellow-50 text-yellow-900",
        info: "border-blue-200 bg-blue-50 text-blue-900",
      },
    },
    defaultVariants: { variant: "info" },
  }
);

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
} as const;

const ICON_COLORS = {
  success: "text-green-600",
  error: "text-red-600",
  warning: "text-yellow-600",
  info: "text-blue-600",
} as const;

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <ToastPrimitive.Provider swipeDirection="right" duration={5000}>
      {toasts.map((t) => {
        const Icon = ICONS[t.variant];
        return (
          <ToastPrimitive.Root
            key={t.id}
            className={cn(toastVariants({ variant: t.variant }))}
            onOpenChange={(open) => { if (!open) dismiss(t.id); }}
            duration={t.duration ?? 5000}
          >
            <Icon className={cn("h-5 w-5 mt-0.5 shrink-0", ICON_COLORS[t.variant])} aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <ToastPrimitive.Title className="text-sm font-semibold">
                {t.title}
              </ToastPrimitive.Title>
              {t.description && (
                <ToastPrimitive.Description className="text-sm opacity-80 mt-1">
                  {t.description}
                </ToastPrimitive.Description>
              )}
              {t.action && (
                <ToastPrimitive.Action altText={t.action.label} asChild>
                  <button
                    onClick={t.action.onClick}
                    className="mt-2 text-sm font-medium underline underline-offset-2 hover:opacity-80"
                  >
                    {t.action.label}
                  </button>
                </ToastPrimitive.Action>
              )}
            </div>
            <ToastPrimitive.Close
              className="shrink-0 rounded-md p-1 opacity-60 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Đóng thông báo"
            >
              <X className="h-4 w-4" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        );
      })}
      <ToastPrimitive.Viewport
        className="fixed top-4 right-4 z-[100] flex max-h-screen w-full max-w-sm flex-col-reverse gap-2"
      />
    </ToastPrimitive.Provider>
  );
}
