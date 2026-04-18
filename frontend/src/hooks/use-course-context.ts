"use client";

import { useEffect } from "react";
import { create } from "zustand";
import { api } from "@/lib/api";
import type { Course, Enrollment, StudentClass } from "@/types";

const STORAGE_KEY = "palp:course-context:v1";

const FALLBACK_COURSE_ID = Number(
  process.env.NEXT_PUBLIC_DEFAULT_COURSE_ID || 1,
) || 1;
const FALLBACK_CLASS_ID = Number(
  process.env.NEXT_PUBLIC_DEFAULT_CLASS_ID || 1,
) || 1;

interface PersistedSelection {
  courseId: number | null;
  classId: number | null;
}

interface CourseContextState {
  loading: boolean;
  error: boolean;
  enrollments: Enrollment[];
  classes: StudentClass[];
  courseId: number | null;
  classId: number | null;
  selectCourse: (id: number) => void;
  selectClass: (id: number) => void;
  loadForStudent: () => Promise<void>;
  loadForLecturer: () => Promise<void>;
  reset: () => void;
}

function readPersisted(): PersistedSelection {
  if (typeof window === "undefined") return { courseId: null, classId: null };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { courseId: null, classId: null };
    const parsed = JSON.parse(raw) as PersistedSelection;
    return {
      courseId: typeof parsed.courseId === "number" ? parsed.courseId : null,
      classId: typeof parsed.classId === "number" ? parsed.classId : null,
    };
  } catch {
    return { courseId: null, classId: null };
  }
}

function persist(selection: PersistedSelection) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
  } catch {
    // localStorage may be disabled in incognito; fail silently.
  }
}

function unwrapList<T>(payload: T[] | { results?: T[] } | null | undefined): T[] {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  if ("results" in payload && Array.isArray(payload.results)) return payload.results;
  return [];
}

export const useCourseContext = create<CourseContextState>((set, get) => ({
  loading: false,
  error: false,
  enrollments: [],
  classes: [],
  courseId: null,
  classId: null,

  selectCourse: (id) => {
    set({ courseId: id });
    persist({ courseId: id, classId: get().classId });
  },

  selectClass: (id) => {
    set({ classId: id });
    persist({ courseId: get().courseId, classId: id });
  },

  loadForStudent: async () => {
    if (get().loading) return;
    set({ loading: true, error: false });
    try {
      const data = await api.get<Enrollment[] | { results?: Enrollment[] }>(
        "/curriculum/my-enrollments/",
      );
      const enrollments = unwrapList<Enrollment>(data);
      const persisted = readPersisted();
      const stillValid = enrollments.find((e) => e.course?.id === persisted.courseId);
      const fallback = enrollments[0];
      const courseId =
        stillValid?.course?.id ??
        fallback?.course?.id ??
        FALLBACK_COURSE_ID;
      const classId =
        enrollments.find((e) => e.course?.id === courseId)?.student_class ??
        persisted.classId ??
        FALLBACK_CLASS_ID;
      set({ enrollments, courseId, classId, loading: false });
      persist({ courseId, classId });
    } catch {
      set({
        loading: false,
        error: true,
        courseId: FALLBACK_COURSE_ID,
        classId: FALLBACK_CLASS_ID,
      });
    }
  },

  loadForLecturer: async () => {
    if (get().loading) return;
    set({ loading: true, error: false });
    try {
      const data = await api.get<StudentClass[] | { results?: StudentClass[] }>(
        "/auth/classes/",
      );
      const classes = unwrapList<StudentClass>(data);
      const courses = await api
        .get<Course[] | { results?: Course[] }>("/curriculum/courses/")
        .catch(() => [] as Course[]);
      const courseList = unwrapList<Course>(courses);
      const persisted = readPersisted();
      const validClass = classes.find((c) => c.id === persisted.classId);
      const validCourse = courseList.find((c) => c.id === persisted.courseId);
      const classId = validClass?.id ?? classes[0]?.id ?? FALLBACK_CLASS_ID;
      const courseId = validCourse?.id ?? courseList[0]?.id ?? FALLBACK_COURSE_ID;
      set({ classes, classId, courseId, loading: false });
      persist({ courseId, classId });
    } catch {
      set({
        loading: false,
        error: true,
        courseId: FALLBACK_COURSE_ID,
        classId: FALLBACK_CLASS_ID,
      });
    }
  },

  reset: () => {
    set({
      enrollments: [],
      classes: [],
      courseId: null,
      classId: null,
      error: false,
      loading: false,
    });
    if (typeof window !== "undefined") {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
      } catch {
        // ignore
      }
    }
  },
}));

/**
 * Resolve the active course id with a safe fallback so callers always get a
 * usable number even before the first network response. Components should
 * still render an empty/error state if `loading` is true and `courseId` is
 * the fallback value to avoid flashing wrong data.
 */
export function resolveCourseId(state: CourseContextState): number {
  return state.courseId ?? FALLBACK_COURSE_ID;
}

export function resolveClassId(state: CourseContextState): number {
  return state.classId ?? FALLBACK_CLASS_ID;
}

/**
 * Hook that ensures the relevant context is loaded the first time a page
 * needs it. Pages call this in `useEffect` to opt into the role-aware fetch.
 */
export function useEnsureCourseContext(role: "student" | "lecturer" | undefined) {
  const loadForStudent = useCourseContext((s) => s.loadForStudent);
  const loadForLecturer = useCourseContext((s) => s.loadForLecturer);
  const courseId = useCourseContext((s) => s.courseId);
  const classId = useCourseContext((s) => s.classId);

  useEffect(() => {
    if (!role) return;
    if (role === "student" && courseId == null) {
      loadForStudent();
    } else if (role === "lecturer" && classId == null) {
      loadForLecturer();
    }
  }, [role, courseId, classId, loadForStudent, loadForLecturer]);
}
