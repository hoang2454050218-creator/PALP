import { describe, it, expect } from 'vitest'
import { cn, formatDuration, formatDate, masteryColor, masteryBg, difficultyLabel } from '../utils'

describe('cn', () => {
  it('combines multiple class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('merges conflicting tailwind classes', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4')
  })

  it('handles conditional classes', () => {
    expect(cn('base', false && 'hidden', 'end')).toBe('base end')
  })
})

describe('formatDuration', () => {
  it('returns "0s" for zero seconds', () => {
    expect(formatDuration(0)).toBe('0s')
  })

  it('returns seconds only when under a minute', () => {
    expect(formatDuration(30)).toBe('30s')
  })

  it('returns minutes and seconds', () => {
    expect(formatDuration(90)).toBe('1m 30s')
  })

  it('returns zero seconds when exact minute', () => {
    expect(formatDuration(60)).toBe('1m 0s')
  })
})

describe('formatDate', () => {
  it('formats ISO date string to vi-VN locale', () => {
    const result = formatDate('2024-01-15T10:30:00Z')
    expect(result).toBeTruthy()
    expect(typeof result).toBe('string')
  })
})

describe('masteryColor', () => {
  it('returns green for mastery >= 0.85', () => {
    expect(masteryColor(0.85)).toBe('text-green-600')
    expect(masteryColor(1.0)).toBe('text-green-600')
  })

  it('returns yellow for mastery between 0.6 and 0.85', () => {
    expect(masteryColor(0.6)).toBe('text-yellow-600')
    expect(masteryColor(0.84)).toBe('text-yellow-600')
  })

  it('returns red for mastery below 0.6', () => {
    expect(masteryColor(0.59)).toBe('text-red-600')
    expect(masteryColor(0)).toBe('text-red-600')
  })
})

describe('masteryBg', () => {
  it('returns green bg for mastery >= 0.85', () => {
    expect(masteryBg(0.85)).toBe('bg-green-500')
    expect(masteryBg(1.0)).toBe('bg-green-500')
  })

  it('returns yellow bg for mastery between 0.6 and 0.85', () => {
    expect(masteryBg(0.6)).toBe('bg-yellow-500')
    expect(masteryBg(0.84)).toBe('bg-yellow-500')
  })

  it('returns red bg for mastery below 0.6', () => {
    expect(masteryBg(0.59)).toBe('bg-red-500')
    expect(masteryBg(0)).toBe('bg-red-500')
  })
})

describe('difficultyLabel', () => {
  it('returns "Dễ" for level 1', () => {
    expect(difficultyLabel(1)).toBe('Dễ')
  })

  it('returns "Trung bình" for level 2', () => {
    expect(difficultyLabel(2)).toBe('Trung bình')
  })

  it('returns "Khó" for level 3', () => {
    expect(difficultyLabel(3)).toBe('Khó')
  })

  it('returns "Unknown" for unmapped levels', () => {
    expect(difficultyLabel(0)).toBe('Unknown')
    expect(difficultyLabel(99)).toBe('Unknown')
  })
})
