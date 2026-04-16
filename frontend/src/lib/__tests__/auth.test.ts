import { describe, it, expect, beforeEach } from 'vitest'
import { getStoredUser, setStoredUser, clearStoredUser, isAuthenticated } from '../auth'
import type { User } from '@/types'

const mockUser: User = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  role: 'student',
  student_id: 'SV001',
  phone: '0123456789',
  avatar_url: '',
  consent_given: true,
  consent_given_at: '2024-01-01T00:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
}

beforeEach(() => {
  localStorage.clear()
})

describe('getStoredUser', () => {
  it('returns null when no user is stored', () => {
    expect(getStoredUser()).toBeNull()
  })

  it('returns parsed user when valid JSON exists', () => {
    localStorage.setItem('user', JSON.stringify(mockUser))
    expect(getStoredUser()).toEqual(mockUser)
  })

  it('returns null when localStorage contains invalid JSON', () => {
    localStorage.setItem('user', '{bad json')
    expect(getStoredUser()).toBeNull()
  })
})

describe('setStoredUser', () => {
  it('stores user as JSON string in localStorage', () => {
    setStoredUser(mockUser)
    expect(JSON.parse(localStorage.getItem('user')!)).toEqual(mockUser)
  })
})

describe('clearStoredUser', () => {
  it('removes user, access_token, and refresh_token', () => {
    localStorage.setItem('user', JSON.stringify(mockUser))
    localStorage.setItem('access_token', 'abc')
    localStorage.setItem('refresh_token', 'def')

    clearStoredUser()

    expect(localStorage.getItem('user')).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })
})

describe('isAuthenticated', () => {
  it('returns true when user is stored', () => {
    localStorage.setItem('user', JSON.stringify(mockUser))
    expect(isAuthenticated()).toBe(true)
  })

  it('returns false when no user is stored', () => {
    expect(isAuthenticated()).toBe(false)
  })
})
