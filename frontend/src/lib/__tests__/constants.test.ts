import { describe, it, expect } from 'vitest'
import {
  API_URL,
  SEVERITY_CONFIG,
  DIFFICULTY_LABELS,
  TRIGGER_LABELS,
  ACTION_LABELS,
  MASTERY_LABELS,
  getMasteryLabel,
} from '../constants'

describe('API_URL', () => {
  it('defaults to http://localhost:8000/api', () => {
    expect(API_URL).toBe('http://localhost:8000/api')
  })
})

describe('SEVERITY_CONFIG', () => {
  it('has green key with correct label', () => {
    expect(SEVERITY_CONFIG.green.label).toBe('Ổn định')
  })

  it('has yellow key with correct label', () => {
    expect(SEVERITY_CONFIG.yellow.label).toBe('Cần theo dõi')
  })

  it('has red key with correct label', () => {
    expect(SEVERITY_CONFIG.red.label).toBe('Cần can thiệp')
  })

  it('each severity has color, dot, icon, and description', () => {
    for (const key of ['green', 'yellow', 'red'] as const) {
      expect(SEVERITY_CONFIG[key]).toHaveProperty('color')
      expect(SEVERITY_CONFIG[key]).toHaveProperty('dot')
      expect(SEVERITY_CONFIG[key]).toHaveProperty('icon')
      expect(SEVERITY_CONFIG[key]).toHaveProperty('description')
      expect(SEVERITY_CONFIG[key].description.length).toBeGreaterThan(0)
    }
  })

  it('severity icons are not color-only (AP-02: explainable state)', () => {
    for (const key of ['green', 'yellow', 'red'] as const) {
      expect(SEVERITY_CONFIG[key].icon).toBeTruthy()
      expect(typeof SEVERITY_CONFIG[key].label).toBe('string')
      expect(SEVERITY_CONFIG[key].label.length).toBeGreaterThan(0)
    }
  })
})

describe('DIFFICULTY_LABELS', () => {
  it('maps level 1 to "Dễ"', () => {
    expect(DIFFICULTY_LABELS[1]).toBe('Dễ')
  })

  it('maps level 2 to "Trung bình"', () => {
    expect(DIFFICULTY_LABELS[2]).toBe('Trung bình')
  })

  it('maps level 3 to "Khó"', () => {
    expect(DIFFICULTY_LABELS[3]).toBe('Khó')
  })
})

describe('TRIGGER_LABELS', () => {
  it('has all four trigger types', () => {
    expect(TRIGGER_LABELS).toEqual({
      inactivity: 'Không hoạt động',
      retry_failure: 'Gặp khó khăn nhiều lần',
      milestone_lag: 'Cần thêm thời gian',
      low_mastery: 'Cần bổ sung kiến thức',
    })
  })

  it('labels are non-judgmental (no "yếu", "kém", "thất bại")', () => {
    const forbidden = ['yếu', 'kém', 'thất bại', 'tệ']
    for (const label of Object.values(TRIGGER_LABELS)) {
      for (const word of forbidden) {
        expect(label.toLowerCase()).not.toContain(word)
      }
    }
  })
})

describe('ACTION_LABELS', () => {
  it('has all three action types', () => {
    expect(ACTION_LABELS).toEqual({
      send_message: 'Gửi tin nhắn',
      suggest_task: 'Gợi ý bài tập',
      schedule_meeting: 'Đặt lịch gặp',
    })
  })
})

describe('MASTERY_LABELS', () => {
  it('has high/medium/low keys', () => {
    expect(MASTERY_LABELS.high).toBe('Đã nắm vững')
    expect(MASTERY_LABELS.medium).toBe('Đang tiến bộ')
    expect(MASTERY_LABELS.low).toBe('Cần bổ sung')
  })
})

describe('getMasteryLabel', () => {
  it('returns high label for mastery >= 0.85', () => {
    expect(getMasteryLabel(0.85)).toBe('Đã nắm vững')
    expect(getMasteryLabel(1.0)).toBe('Đã nắm vững')
  })

  it('returns medium label for mastery 0.6-0.84', () => {
    expect(getMasteryLabel(0.6)).toBe('Đang tiến bộ')
    expect(getMasteryLabel(0.84)).toBe('Đang tiến bộ')
  })

  it('returns low label for mastery < 0.6', () => {
    expect(getMasteryLabel(0.59)).toBe('Cần bổ sung')
    expect(getMasteryLabel(0)).toBe('Cần bổ sung')
  })

  it('thresholds align with BKT pathway rules (PATH-001..003)', () => {
    expect(getMasteryLabel(0.59)).toBe(MASTERY_LABELS.low)
    expect(getMasteryLabel(0.60)).toBe(MASTERY_LABELS.medium)
    expect(getMasteryLabel(0.85)).toBe(MASTERY_LABELS.high)
  })
})
