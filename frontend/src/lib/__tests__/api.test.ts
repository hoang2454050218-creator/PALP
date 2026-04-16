import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { api } from '../api'

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
    location: { href: '' },
    localStorage: globalThis.localStorage,
  })
  mockFetch.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

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

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Not found' }),
    })

    await expect(api.get('/missing/')).rejects.toThrow('Not found')
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

    await expect(api.get('/protected/')).rejects.toThrow('Session expired')
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

    await expect(api.get('/bad/')).rejects.toThrow('Validation failed')
  })

  it('falls back to status code on non-JSON error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('not json')
      },
    })

    await expect(api.get('/error/')).rejects.toThrow('API Error: 500')
  })
})
