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
  it('returns success for mastery >= 0.85', () => {
    expect(masteryColor(0.85)).toBe('text-success')
    expect(masteryColor(1.0)).toBe('text-success')
  })

  it('returns warning for mastery between 0.6 and 0.85', () => {
    expect(masteryColor(0.6)).toBe('text-warning')
    expect(masteryColor(0.84)).toBe('text-warning')
  })

  it('returns danger for mastery below 0.6', () => {
    expect(masteryColor(0.59)).toBe('text-danger')
    expect(masteryColor(0)).toBe('text-danger')
  })
})

describe('masteryBg', () => {
  it('returns success bg for mastery >= 0.85', () => {
    expect(masteryBg(0.85)).toBe('bg-success')
    expect(masteryBg(1.0)).toBe('bg-success')
  })

  it('returns warning bg for mastery between 0.6 and 0.85', () => {
    expect(masteryBg(0.6)).toBe('bg-warning')
    expect(masteryBg(0.84)).toBe('bg-warning')
  })

  it('returns danger bg for mastery below 0.6', () => {
    expect(masteryBg(0.59)).toBe('bg-danger')
    expect(masteryBg(0)).toBe('bg-danger')
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
