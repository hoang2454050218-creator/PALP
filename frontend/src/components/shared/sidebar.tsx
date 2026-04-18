"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, BookOpen, Route, ClipboardCheck,
  AlertTriangle, History, LogOut, GraduationCap,
  Shield, Network, Settings, X, Heart,
} from "lucide-react";
import { cn, displayName } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { useCourseContext } from "@/hooks/use-course-context";
import { Button } from "@/components/ui/button";
import { CourseSelector } from "@/components/shared/course-selector";

const ROLE_LABELS: Record<string, string> = {
  student: "Sinh viên",
  lecturer: "Giảng viên",
  admin: "Quản trị viên",
};

const studentNav = [
  { href: "/dashboard", label: "Tổng quan", icon: LayoutDashboard },
  { href: "/assessment", label: "Đánh giá đầu vào", icon: ClipboardCheck },
  { href: "/pathway", label: "Lộ trình học", icon: Route },
  { href: "/task", label: "Bài tập", icon: BookOpen },
  { href: "/wellbeing", label: "Sức khỏe học tập", icon: Heart },
  { href: "/preferences", label: "Tùy chỉnh", icon: Settings },
  { href: "/privacy", label: "Quyền riêng tư", icon: Shield },
];

const lecturerNav = [
  { href: "/overview", label: "Tổng quan lớp", icon: LayoutDashboard },
  { href: "/alerts", label: "Cảnh báo", icon: AlertTriangle },
  { href: "/knowledge-graph", label: "Đồ thị kiến thức", icon: Network },
  { href: "/history", label: "Lịch sử can thiệp", icon: History },
  { href: "/preferences", label: "Tùy chỉnh", icon: Settings },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ mobileOpen = false, onMobileClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const resetCourseContext = useCourseContext((s) => s.reset);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  const navItems = user?.role === "lecturer" || user?.role === "admin" ? lecturerNav : studentNav;

  const handleLogout = async () => {
    await logout();
    resetCourseContext();
    router.replace("/login");
  };

  useEffect(() => {
    if (!mobileOpen) return;
    closeRef.current?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onMobileClose?.();
      if (e.key === "Tab" && sidebarRef.current) {
        const focusable = sidebarRef.current.querySelectorAll<HTMLElement>(
          'a, button, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [mobileOpen, onMobileClose]);

  useEffect(() => {
    if (mobileOpen) onMobileClose?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const sidebarContent = (
    <>
      <div className="flex h-16 items-center justify-between border-b px-6">
        <div className="flex items-center gap-2">
          <GraduationCap className="h-7 w-7 text-primary" aria-hidden="true" />
          <div>
            <h1 className="text-lg font-bold text-primary">PALP</h1>
            <p className="text-[10px] text-muted-foreground leading-tight">
              Personalized Adaptive Learning
            </p>
          </div>
        </div>
        {onMobileClose && (
          <Button
            ref={closeRef}
            variant="ghost"
            size="sm"
            className="lg:hidden p-2"
            onClick={onMobileClose}
            aria-label="Đóng menu"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </Button>
        )}
      </div>

      <div className="border-b px-4 py-3">
        <CourseSelector />
      </div>

      <nav className="flex-1 space-y-1 p-4" aria-label="Điều hướng chính">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-4">
        <div className="mb-3 flex items-center gap-3 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary text-sm font-semibold" aria-hidden="true">
            {(user?.first_name?.[0] || user?.username?.[0] || "U").toUpperCase()}
          </div>
          <div className="flex-1 truncate">
            <p className="text-sm font-medium truncate">
              {displayName(user, "Khách")}
            </p>
            <p className="text-xs text-muted-foreground">
              {user?.role ? ROLE_LABELS[user.role] ?? user.role : ""}
            </p>
          </div>
        </div>
        <Button variant="ghost" size="sm" className="w-full justify-start gap-2" onClick={handleLogout}>
          <LogOut className="h-4 w-4" aria-hidden="true" />
          Đăng xuất
        </Button>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex h-screen w-64 flex-col border-r bg-card shrink-0">
        {sidebarContent}
      </aside>

      {/* Mobile drawer overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-50 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Menu điều hướng"
        >
          <div
            className="fixed inset-0 bg-black/50"
            onClick={onMobileClose}
            aria-hidden="true"
          />
          <aside
            ref={sidebarRef}
            className="fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-card shadow-xl animate-in slide-in-from-left duration-200"
          >
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}
