import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useApiCall } from '../use-api-call'
import { ApiError } from '@/lib/api'

const toastMock = vi.fn()
vi.mock('@/hooks/use-toast', () => ({
  toast: (...args: unknown[]) => toastMock(...args),
  useToast: () => ({ toasts: [], dismiss: vi.fn() }),
}))

beforeEach(() => {
  toastMock.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useApiCall', () => {
  it('starts in idle status', () => {
    const { result } = renderHook(() => useApiCall<number>())
    expect(result.current.status).toBe('idle')
    expect(result.current.data).toBeNull()
  })

  it('transitions to success and returns data', async () => {
    const { result } = renderHook(() => useApiCall<number>())
    let returned: number | null = null
    await act(async () => {
      returned = await result.current.run(async () => 42)
    })
    expect(returned).toBe(42)
    expect(result.current.status).toBe('success')
    expect(result.current.data).toBe(42)
    expect(toastMock).not.toHaveBeenCalled()
  })

  it('surfaces toast on ApiError', async () => {
    const { result } = renderHook(() => useApiCall<number>())
    await act(async () => {
      await result.current.run(async () => {
        throw new ApiError({ status: 500, detail: 'boom' })
      })
    })
    expect(result.current.status).toBe('error')
    expect(result.current.error?.status).toBe(500)
    expect(toastMock).toHaveBeenCalledTimes(1)
  })

  it('does NOT toast on 401 (handled by api client redirect)', async () => {
    const { result } = renderHook(() => useApiCall<number>())
    await act(async () => {
      await result.current.run(async () => {
        throw new ApiError({ status: 401, detail: 'auth' })
      })
    })
    expect(toastMock).not.toHaveBeenCalled()
  })

  it('treats 404 as empty when configured', async () => {
    const { result } = renderHook(() => useApiCall<number>({ treat404AsEmpty: true }))
    await act(async () => {
      await result.current.run(async () => {
        throw new ApiError({ status: 404, detail: 'missing' })
      })
    })
    expect(result.current.status).toBe('success')
    expect(result.current.data).toBeNull()
    expect(toastMock).not.toHaveBeenCalled()
  })

  it('reset returns state to idle', async () => {
    const { result } = renderHook(() => useApiCall<number>())
    await act(async () => {
      await result.current.run(async () => 10)
    })
    act(() => result.current.reset())
    expect(result.current.status).toBe('idle')
    expect(result.current.data).toBeNull()
  })
})
