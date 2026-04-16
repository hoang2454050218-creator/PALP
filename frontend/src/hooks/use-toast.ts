import { create } from "zustand";

export interface Toast {
  id: string;
  variant: "success" | "error" | "warning" | "info";
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  duration?: number;
}

interface ToastStore {
  toasts: Toast[];
  add: (toast: Omit<Toast, "id">) => void;
  dismiss: (id: string) => void;
}

export const useToast = create<ToastStore>((set) => ({
  toasts: [],
  add: (toast) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }));
    const duration = toast.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => {
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
      }, duration);
    }
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export function toast(t: Omit<Toast, "id">) {
  useToast.getState().add(t);
}
