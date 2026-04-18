import { describe, it, expect } from 'vitest'
import { masteryColor, masteryBg, formatDuration, formatDate } from '../utils'
import { getMasteryLabel, SEVERITY_CONFIG, TRIGGER_LABELS } from '../constants'

/**
 * Tests that verify frontend display logic aligns with BKT pathway rules.
 * QA_STANDARD PATH-001..003: P<0.60 supplement, 0.60-0.85 continue, >0.85 advance.
 */

describe('Mastery thresholds alignment with BKT rules', () => {
  const LOW = [0, 0.1, 0.3, 0.59]
  const MID = [0.6, 0.7, 0.84]
  const HIGH = [0.85, 0.9, 1.0]

  describe('PATH-001: P < 0.60 -> supplement (danger/low)', () => {
    it.each(LOW)('mastery %f -> danger color', (p) => {
      expect(masteryColor(p)).toBe('text-danger')
    })

    it.each(LOW)('mastery %f -> danger bg', (p) => {
      expect(masteryBg(p)).toBe('bg-danger')
    })

    it.each(LOW)('mastery %f -> "Cần bổ sung" label', (p) => {
      expect(getMasteryLabel(p)).toBe('Cần bổ sung')
    })
  })

  describe('PATH-002: 0.60 <= P <= 0.85 -> continue (warning/medium)', () => {
    it.each(MID)('mastery %f -> warning color', (p) => {
      expect(masteryColor(p)).toBe('text-warning')
    })

    it.each(MID)('mastery %f -> warning bg', (p) => {
      expect(masteryBg(p)).toBe('bg-warning')
    })

    it.each(MID)('mastery %f -> "Đang tiến bộ" label', (p) => {
      expect(getMasteryLabel(p)).toBe('Đang tiến bộ')
    })
  })

  describe('PATH-003: P > 0.85 -> advance (success/high)', () => {
    it.each(HIGH)('mastery %f -> success color', (p) => {
      expect(masteryColor(p)).toBe('text-success')
    })

    it.each(HIGH)('mastery %f -> success bg', (p) => {
      expect(masteryBg(p)).toBe('bg-success')
    })

    it.each(HIGH)('mastery %f -> "Đã nắm vững" label', (p) => {
      expect(getMasteryLabel(p)).toBe('Đã nắm vững')
    })
  })

  describe('Boundary exactness', () => {
    it('0.60 is warning (not danger)', () => {
      expect(masteryColor(0.6)).toBe('text-warning')
      expect(getMasteryLabel(0.6)).toBe('Đang tiến bộ')
    })

    it('0.85 is success (not warning)', () => {
      expect(masteryColor(0.85)).toBe('text-success')
      expect(getMasteryLabel(0.85)).toBe('Đã nắm vững')
    })

    it('0.5999 is danger', () => {
      expect(masteryColor(0.5999)).toBe('text-danger')
    })

    it('0.8499 is warning', () => {
      expect(masteryColor(0.8499)).toBe('text-warning')
    })
  })
})

describe('Severity display is not color-only (FE-021, AP-02)', () => {
  it('each severity has icon AND text label', () => {
    for (const key of ['green', 'yellow', 'red'] as const) {
      const cfg = SEVERITY_CONFIG[key]
      expect(cfg.icon).toBeTruthy()
      expect(cfg.label.length).toBeGreaterThan(0)
      expect(cfg.description.length).toBeGreaterThan(0)
    }
  })

  it('trigger labels use non-judgmental wording (FE-026)', () => {
    const forbidden = ['yếu', 'kém', 'thất bại', 'tệ', 'dốt', 'lười']
    for (const label of Object.values(TRIGGER_LABELS)) {
      for (const word of forbidden) {
        expect(label.toLowerCase()).not.toContain(word)
      }
    }
  })
})

describe('Duration formatting edge cases', () => {
  it('0 seconds', () => {
    expect(formatDuration(0)).toBe('0s')
  })

  it('exactly 1 minute', () => {
    expect(formatDuration(60)).toBe('1m 0s')
  })

  it('15 minutes (assessment time budget)', () => {
    expect(formatDuration(900)).toBe('15m 0s')
  })

  it('large duration (session > 1 hour)', () => {
    const result = formatDuration(3661)
    expect(result).toBe('61m 1s')
  })
})

describe('Date formatting', () => {
  it('formats ISO string to Vietnamese locale', () => {
    const result = formatDate('2026-04-16T10:30:00Z')
    expect(result).toBeTruthy()
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(5)
  })

  it('handles different timezones', () => {
    const result = formatDate('2026-01-01T00:00:00+07:00')
    expect(result).toBeTruthy()
  })
})
