import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { api, ApiError } from '../api'

const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch)
  vi.stubGlobal('localStorage', {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    length: 0,
    key: vi.fn(),
  })
  vi.stubGlobal('window', {
    location: { href: '', pathname: '/dashboard' },
    localStorage: globalThis.localStorage,
  })
  mockFetch.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

async function expectApiError(promise: Promise<unknown>): Promise<ApiError> {
  const err = await promise.catch((e) => e)
  if (!(err instanceof ApiError)) {
    throw new Error(`Expected ApiError, got ${typeof err}: ${err}`)
  }
  return err
}

describe('ApiClient.get', () => {
  it('calls fetch with correct URL and credentials', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: 'test' }),
    })

    const result = await api.get('/auth/profile/')
    expect(result).toEqual({ data: 'test' })
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/auth/profile/'),
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('throws ApiError with parsed detail on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Not found' }),
    })

    const err = await expectApiError(api.get('/missing/'))
    expect(err.status).toBe(404)
    expect(err.detail).toBe('Not found')
    expect(err.isNotFound()).toBe(true)
  })

  it('returns undefined for 204 No Content', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204, json: async () => ({}) })
    const result = await api.get('/empty/')
    expect(result).toBeUndefined()
  })
})

describe('ApiClient.post', () => {
  it('sends POST with JSON body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => ({ id: 1 }),
    })

    const result = await api.post('/events/track/', { event_name: 'page_view' })
    expect(result).toEqual({ id: 1 })

    const [, options] = mockFetch.mock.calls[0]
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({ event_name: 'page_view' })
  })

  it('does NOT retry POST on 502 (non-idempotent)', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({ detail: 'Bad gateway' }),
    })

    await expect(api.post('/x/', {})).rejects.toBeInstanceOf(ApiError)
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })
})

describe('ApiClient.patch', () => {
  it('sends PATCH request', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ updated: true }),
    })

    await api.patch('/auth/profile/', { first_name: 'New' })

    const [, options] = mockFetch.mock.calls[0]
    expect(options.method).toBe('PATCH')
  })
})

describe('ApiClient.delete', () => {
  it('sends DELETE request', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      json: async () => ({}),
    })

    await api.delete('/some/resource/')

    const [, options] = mockFetch.mock.calls[0]
    expect(options.method).toBe('DELETE')
  })
})

describe('ApiClient token refresh on 401', () => {
  it('retries request after successful refresh', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ data: 'refreshed' }) })

    const result = await api.get('/protected/')
    expect(result).toEqual({ data: 'refreshed' })
    expect(mockFetch).toHaveBeenCalledTimes(3)
  })

  it('clears tokens and redirects on failed refresh', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })

    const err = await expectApiError(api.get('/protected/'))
    expect(err.code).toBe('session_expired')
    expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
    expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
    expect(localStorage.removeItem).toHaveBeenCalledWith('user')
  })
})

describe('ApiClient.login', () => {
  it('sends credentials and returns tokens', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ access: 'abc', refresh: 'def' }),
    })

    const result = await api.login('student1', 'pass123')
    expect(result.access).toBe('abc')
    expect(result.refresh).toBe('def')
  })
})

describe('ApiClient.logout', () => {
  it('calls logout endpoint and clears tokens', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({}),
    })

    await api.logout()
    expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
    expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
    expect(localStorage.removeItem).toHaveBeenCalledWith('user')
  })

  it('clears tokens even if server logout fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    await api.logout()
    expect(localStorage.removeItem).toHaveBeenCalledWith('user')
  })
})

describe('Error handling', () => {
  it('extracts detail field from error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Validation failed' }),
    })

    const err = await expectApiError(api.get('/bad/'))
    expect(err.detail).toBe('Validation failed')
    expect(err.status).toBe(400)
  })

  it('falls back to status code on non-JSON error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('not json')
      },
    })

    const err = await expectApiError(api.get('/error/'))
    expect(err.detail).toMatch(/API Error/)
    expect(err.status).toBe(500)
  })

  it('parses field errors from DRF response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({
        detail: 'Validation failed',
        username: ['Username is required'],
        password: ['Password too short', 'Must contain digit'],
      }),
    })

    const err = await expectApiError(api.post('/auth/register/', {}))
    expect(err.fieldErrors.username).toEqual(['Username is required'])
    expect(err.fieldErrors.password).toEqual(['Password too short', 'Must contain digit'])
  })

  it('treats network failure as ApiError status 0', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'))

    const err = await expectApiError(api.get('/x/'))
    expect(err.status).toBe(0)
    expect(err.code).toBe('network_error')
  })
})

describe('Retry policy', () => {
  it('retries idempotent GET on 503 once and then succeeds', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: 'down' }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ ok: true }) })

    const result = await api.get('/health/')
    expect(result).toEqual({ ok: true })
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })
})
