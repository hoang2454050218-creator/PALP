import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useCourseContext, resolveCourseId, resolveClassId } from '../use-course-context'

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

import { api } from '@/lib/api'

interface FakeStorage {
  _store: Record<string, string>
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
  clear(): void
  length: number
  key(): string | null
}

beforeEach(() => {
  const fake: FakeStorage = {
    _store: {},
    getItem(key) { return this._store[key] ?? null },
    setItem(key, value) { this._store[key] = String(value) },
    removeItem(key) { delete this._store[key] },
    clear() { this._store = {} },
    length: 0,
    key() { return null },
  }
  vi.stubGlobal('localStorage', fake)
  vi.stubGlobal('window', { localStorage: fake })
  useCourseContext.setState({
    enrollments: [],
    classes: [],
    courseId: null,
    classId: null,
    loading: false,
    error: false,
  })
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.clearAllMocks()
})

describe('useCourseContext.loadForStudent', () => {
  it('hydrates enrollments and selects the first course', async () => {
    vi.mocked(api.get).mockResolvedValueOnce([
      {
        id: 1,
        student: 1,
        course: { id: 7, code: 'SBVL', name: 'Sức Bền Vật Liệu', description: '', credits: 3, concept_count: 10, milestone_count: 4 },
        student_class: 11,
        semester: '2025-1',
        enrolled_at: '2025-01-01',
        is_active: true,
      },
    ])
    await useCourseContext.getState().loadForStudent()
    const state = useCourseContext.getState()
    expect(state.courseId).toBe(7)
    expect(state.classId).toBe(11)
    expect(state.enrollments).toHaveLength(1)
    expect(state.error).toBe(false)
  })

  it('falls back to default ids when enrollments fetch fails', async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error('boom'))
    await useCourseContext.getState().loadForStudent()
    const state = useCourseContext.getState()
    expect(state.error).toBe(true)
    expect(state.courseId).toBeGreaterThan(0)
    expect(state.classId).toBeGreaterThan(0)
  })

  it('honours persisted selection when still valid', async () => {
    globalThis.localStorage.setItem(
      'palp:course-context:v1',
      JSON.stringify({ courseId: 9, classId: 22 }),
    )
    vi.mocked(api.get).mockResolvedValueOnce([
      { id: 1, student: 1, course: { id: 7, code: '', name: 'A', description: '', credits: 3, concept_count: 0, milestone_count: 0 }, student_class: 11, semester: '', enrolled_at: '', is_active: true },
      { id: 2, student: 1, course: { id: 9, code: '', name: 'B', description: '', credits: 3, concept_count: 0, milestone_count: 0 }, student_class: 22, semester: '', enrolled_at: '', is_active: true },
    ])
    await useCourseContext.getState().loadForStudent()
    expect(useCourseContext.getState().courseId).toBe(9)
  })
})

describe('useCourseContext.selectCourse', () => {
  it('updates state and persists to localStorage', () => {
    useCourseContext.getState().selectCourse(42)
    expect(useCourseContext.getState().courseId).toBe(42)
    const persisted = JSON.parse(globalThis.localStorage.getItem('palp:course-context:v1') || '{}')
    expect(persisted.courseId).toBe(42)
  })
})

describe('resolveCourseId / resolveClassId helpers', () => {
  it('returns courseId from state when set', () => {
    expect(resolveCourseId({ ...useCourseContext.getState(), courseId: 5 })).toBe(5)
  })

  it('falls back when courseId is null', () => {
    expect(resolveCourseId({ ...useCourseContext.getState(), courseId: null })).toBeGreaterThan(0)
  })

  it('returns classId from state when set', () => {
    expect(resolveClassId({ ...useCourseContext.getState(), classId: 8 })).toBe(8)
  })
})

describe('useCourseContext.reset', () => {
  it('clears state and localStorage', () => {
    useCourseContext.getState().selectCourse(1)
    useCourseContext.getState().reset()
    expect(useCourseContext.getState().courseId).toBeNull()
    expect(globalThis.localStorage.getItem('palp:course-context:v1')).toBeNull()
  })
})
