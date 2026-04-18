"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronsUpDown, Check, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { useCourseContext, useEnsureCourseContext } from "@/hooks/use-course-context";

interface Option {
  id: number;
  label: string;
  hint?: string;
}

export function CourseSelector({ collapsed = false }: { collapsed?: boolean }) {
  const { user } = useAuth();
  const role = user?.role === "lecturer" || user?.role === "admin" ? "lecturer" : "student";
  useEnsureCourseContext(role);

  const enrollments = useCourseContext((s) => s.enrollments);
  const classes = useCourseContext((s) => s.classes);
  const courseId = useCourseContext((s) => s.courseId);
  const classId = useCourseContext((s) => s.classId);
  const selectCourse = useCourseContext((s) => s.selectCourse);
  const selectClass = useCourseContext((s) => s.selectClass);

  const isStudent = role === "student";

  const options = useMemo<Option[]>(() => {
    if (isStudent) {
      return enrollments
        .filter((e) => e.course)
        .map((e) => ({
          id: e.course.id,
          label: e.course.name,
          hint: e.course.code,
        }));
    }
    return classes.map((c) => ({
      id: c.id,
      label: c.name,
      hint: c.academic_year,
    }));
  }, [isStudent, enrollments, classes]);

  const activeId = isStudent ? courseId : classId;
  const active = options.find((o) => o.id === activeId);

  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    if (open) {
      document.addEventListener("mousedown", onClick);
      document.addEventListener("keydown", onKey);
      return () => {
        document.removeEventListener("mousedown", onClick);
        document.removeEventListener("keydown", onKey);
      };
    }
  }, [open]);

  const onSelect = (id: number) => {
    if (isStudent) selectCourse(id);
    else selectClass(id);
    setOpen(false);
    triggerRef.current?.focus();
  };

  if (options.length === 0) return null;

  if (collapsed) {
    return (
      <div className="flex items-center justify-center py-2" aria-hidden="true">
        <BookOpen className="h-4 w-4 text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={isStudent ? "Chọn khóa học" : "Chọn lớp học"}
        className={cn(
          "flex w-full items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-left text-sm transition-colors",
          "hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        )}
      >
        <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <div className="truncate font-medium">
            {active?.label ?? (isStudent ? "Chọn khóa học" : "Chọn lớp")}
          </div>
          {active?.hint && (
            <div className="truncate text-xs text-muted-foreground">{active.hint}</div>
          )}
        </div>
        <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" aria-hidden="true" />
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label={isStudent ? "Danh sách khóa học" : "Danh sách lớp học"}
          className="absolute z-30 mt-1 w-full overflow-hidden rounded-lg border border-border bg-popover shadow-lg"
        >
          {options.map((opt) => {
            const selected = opt.id === activeId;
            return (
              <li key={opt.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => onSelect(opt.id)}
                  className={cn(
                    "flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors",
                    "hover:bg-accent focus-visible:outline-none focus-visible:bg-accent",
                    selected && "bg-primary/10 text-primary",
                  )}
                >
                  <Check
                    className={cn(
                      "h-4 w-4 shrink-0",
                      selected ? "opacity-100" : "opacity-0",
                    )}
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">{opt.label}</div>
                    {opt.hint && (
                      <div className="truncate text-xs text-muted-foreground">{opt.hint}</div>
                    )}
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
