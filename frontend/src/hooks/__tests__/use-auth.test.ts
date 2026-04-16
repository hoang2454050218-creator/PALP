import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuth } from '../use-auth'
import type { User } from '@/types'

vi.mock('@/lib/api', () => ({
  api: {
    login: vi.fn(),
    logout: vi.fn(),
    get: vi.fn(),
  },
}))

const mockUser: User = {
  id: 1,
  username: 'student1',
  email: 'student@example.com',
  first_name: 'Student',
  last_name: 'One',
  role: 'student',
  student_id: 'SV001',
  phone: '',
  avatar_url: '',
  consent_given: true,
  consent_given_at: null,
  created_at: '2024-01-01T00:00:00Z',
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  useAuth.setState({ user: null, loading: true, consentPending: false })
})

describe('useAuth', () => {
  it('has correct initial state', () => {
    const state = useAuth.getState()
    expect(state.user).toBeNull()
    expect(state.loading).toBe(true)
    expect(state.consentPending).toBe(false)
  })

  describe('initialize', () => {
    it('loads user from localStorage and sets loading to false', () => {
      localStorage.setItem('user', JSON.stringify(mockUser))
      useAuth.getState().initialize()

      const state = useAuth.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.loading).toBe(false)
    })

    it('sets user to null when no stored user exists', () => {
      useAuth.getState().initialize()

      const state = useAuth.getState()
      expect(state.user).toBeNull()
      expect(state.loading).toBe(false)
    })
  })

  describe('login', () => {
    it('calls api.login, fetches profile, and stores user', async () => {
      const { api } = await import('@/lib/api')
      vi.mocked(api.login).mockResolvedValue({ access: 'a', refresh: 'r' })
      vi.mocked(api.get)
        .mockResolvedValueOnce(mockUser)
        .mockResolvedValueOnce([{ granted: true }])

      await useAuth.getState().login('student1', 'pass')

      expect(api.login).toHaveBeenCalledWith('student1', 'pass')
      expect(api.get).toHaveBeenCalledWith('/auth/profile/')
      expect(useAuth.getState().user).toEqual(mockUser)
    })
  })

  describe('logout', () => {
    it('clears user and consent state', async () => {
      const { api } = await import('@/lib/api')
      vi.mocked(api.logout).mockResolvedValue(undefined)

      useAuth.setState({ user: mockUser, consentPending: true })
      await useAuth.getState().logout()

      const state = useAuth.getState()
      expect(state.user).toBeNull()
      expect(state.consentPending).toBe(false)
      expect(api.logout).toHaveBeenCalled()
    })
  })

  describe('dismissConsentModal', () => {
    it('sets consentPending to false', () => {
      useAuth.setState({ consentPending: true })
      useAuth.getState().dismissConsentModal()
      expect(useAuth.getState().consentPending).toBe(false)
    })
  })
})
