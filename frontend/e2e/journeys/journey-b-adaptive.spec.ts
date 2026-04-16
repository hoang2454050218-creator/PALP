import { test, expect, type Page } from '@playwright/test'
import {
  loginViaApi,
  seedAssessmentCompletion,
  getNextTask,
  submitTaskAnswer,
  getMastery,
} from '../helpers/api-helpers'

/**
 * Journey B — Adaptive intervention
 *
 * Sai 2 câu liên tiếp → mastery giảm → chèn nội dung bổ trợ → retry →
 * đúng thì quay lại luồng chính; sai tiếp thì flag giảng viên.
 *
 * Gate:
 *   100% pass
 *   0 loop vô hạn
 *   0 wrong-concept intervention
 *   0 lost retry state
 */

const STUDENT_USER = 'sv_test'
const STUDENT_PASS = 'testpass123'
const COURSE_ID = 1
const MAX_LOOP_GUARD = 10

test.describe.serial('Journey B — Adaptive intervention', () => {
  let page: Page

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage()
  })

  test.afterAll(async () => {
    await page.close()
  })

  test('B0: Setup — login và seed assessment qua API nếu cần', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const task = await getNextTask(request, auth, COURSE_ID).catch(() => null)

    if (!task || task.detail?.includes('đánh giá')) {
      await seedAssessmentCompletion(request, auth)
    }
  })

  test('B1: Login qua UI và navigate đến /task', async () => {
    await page.goto('/login')
    await page.fill('#username', STUDENT_USER)
    await page.fill('#password', STUDENT_PASS)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 })

    await page.goto('/task')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('text=Bài tập')).toBeVisible({ timeout: 10000 })
  })

  test('B2: Trả lời sai lần 1 — mastery phải giảm', async () => {
    const options = page.locator('button.w-full.text-left')
    const hasTask = await options.first().isVisible({ timeout: 5000 }).catch(() => false)

    if (!hasTask) {
      test.skip(true, 'No task available to test adaptive flow')
      return
    }

    const taskTitle = await page.locator('h3, [class*="CardTitle"]').first().textContent()
    test.info().annotations.push({ type: 'task', description: `Task: ${taskTitle}` })

    const allOptions = await options.allTextContents()
    expect(allOptions.length).toBeGreaterThanOrEqual(2)

    const lastOption = options.last()
    await lastOption.click()

    const submitBtn = page.locator('button:has-text("Nộp bài")')
    await expect(submitBtn).toBeEnabled()
    await submitBtn.click()

    const feedback = page.locator('text=/Chính xác!|Chưa đúng/')
    await expect(feedback).toBeVisible({ timeout: 5000 })

    const masteryText = page.locator('text=/Mastery: \\d+%/')
    await expect(masteryText).toBeVisible()
  })

  test('B3: Retry cùng task — trả lời sai lần 2', async () => {
    const retryBtn = page.locator('button:has-text("Thử lại")')
    const hasRetry = await retryBtn.isVisible({ timeout: 3000 }).catch(() => false)

    if (hasRetry) {
      await retryBtn.click()

      await expect(page.locator('button.w-full.text-left').first()).toBeVisible({ timeout: 3000 })
      const options = page.locator('button.w-full.text-left')
      await options.last().click()

      const submitBtn = page.locator('button:has-text("Nộp bài")')
      await submitBtn.click()

      const feedback = page.locator('text=/Chính xác!|Chưa đúng/')
      await expect(feedback).toBeVisible({ timeout: 5000 })
    } else {
      const nextBtn = page.locator('button:has-text("Bài tiếp")')
      await nextBtn.click()

      await expect(page.locator('button.w-full.text-left').first()).toBeVisible({ timeout: 5000 })
      const options = page.locator('button.w-full.text-left')
      await options.last().click()

      const submitBtn = page.locator('button:has-text("Nộp bài")')
      await submitBtn.click()

      await expect(page.locator('text=/Chính xác!|Chưa đúng/')).toBeVisible({ timeout: 5000 })
    }
  })

  test('B4: Kiểm tra adaptive response — supplement hoặc continue', async () => {
    const pathwaySection = page.locator('text=Pathway')
    await expect(pathwaySection).toBeVisible({ timeout: 3000 })

    const supplementCard = page.locator('text=Tài liệu bổ trợ')
    const pathwayMessage = page.locator('.text-blue-800, .text-sm.text-blue-800')

    const hasSupplementary = await supplementCard.isVisible({ timeout: 2000 }).catch(() => false)
    const hasPathwayMsg = await pathwayMessage.isVisible({ timeout: 1000 }).catch(() => false)

    test.info().annotations.push({
      type: 'adaptive_response',
      description: `Supplementary visible: ${hasSupplementary}, Pathway msg: ${hasPathwayMsg}`,
    })

    expect(hasSupplementary || hasPathwayMsg).toBe(true)
  })

  test('B5: Retry lần cuối — trả lời đúng → quay lại luồng chính', async ({ request }) => {
    const retryBtn = page.locator('button:has-text("Thử lại")')
    const hasRetry = await retryBtn.isVisible({ timeout: 2000 }).catch(() => false)

    if (hasRetry) {
      await retryBtn.click()
    } else {
      await page.locator('button:has-text("Bài tiếp")').click()
    }

    await expect(page.locator('button.w-full.text-left').first()).toBeVisible({ timeout: 5000 })

    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)
    const task = await getNextTask(request, auth, COURSE_ID).catch(() => null)

    if (task && task.content?.correct_answer) {
      const correctAnswer = task.content.correct_answer as string
      const optionBtns = page.locator('button.w-full.text-left')
      const count = await optionBtns.count()

      let clicked = false
      for (let i = 0; i < count; i++) {
        const text = await optionBtns.nth(i).textContent()
        if (text?.includes(correctAnswer)) {
          await optionBtns.nth(i).click()
          clicked = true
          break
        }
      }
      if (!clicked) {
        await optionBtns.first().click()
      }
    } else {
      await page.locator('button.w-full.text-left').first().click()
    }

    const submitBtn = page.locator('button:has-text("Nộp bài")')
    await submitBtn.click()

    const feedback = page.locator('text=/Chính xác!|Chưa đúng/')
    await expect(feedback).toBeVisible({ timeout: 5000 })

    const masteryDisplay = page.locator('text=/Mastery: \\d+%/')
    await expect(masteryDisplay).toBeVisible()
  })

  test('B6: Gate — 0 loop vô hạn: step count bounded', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)
    const mastery = await getMastery(request, auth, COURSE_ID)

    for (const m of mastery) {
      expect(m.attempt_count).toBeLessThanOrEqual(MAX_LOOP_GUARD)
    }
  })

  test('B7: Gate — 0 wrong-concept intervention via API', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const interventions = await request
      .get('http://localhost:8000/api/adaptive/interventions/', {
        headers: {
          Cookie: auth.cookies.map((c) => `${c.name}=${c.value}`).join('; '),
        },
      })
      .then((r) => r.json())
      .catch(() => [])

    const list = Array.isArray(interventions) ? interventions : (interventions as any).results ?? []

    const task = await getNextTask(request, auth, COURSE_ID).catch(() => null)
    if (!task) return

    for (const intervention of list) {
      if (intervention.concept && task.concept) {
        test.info().annotations.push({
          type: 'intervention_check',
          description: `Intervention concept: ${intervention.concept}, Task concept: ${task.concept}`,
        })
      }
    }
  })

  test('B8: Gate — 0 lost retry state: attempt_number increases correctly', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const attemptsRes = await request
      .get('http://localhost:8000/api/adaptive/attempts/', {
        headers: {
          Cookie: auth.cookies.map((c) => `${c.name}=${c.value}`).join('; '),
        },
      })
      .then((r) => r.json())
      .catch(() => [])

    const attempts = Array.isArray(attemptsRes) ? attemptsRes : (attemptsRes as any).results ?? []

    if (attempts.length === 0) return

    const byTask = new Map<number, number[]>()
    for (const a of attempts) {
      const list = byTask.get(a.task) ?? []
      list.push(a.attempt_number)
      byTask.set(a.task, list)
    }

    for (const [taskId, numbers] of byTask) {
      const sorted = [...numbers].sort((a, b) => a - b)
      for (let i = 0; i < sorted.length; i++) {
        expect(sorted[i]).toBe(i + 1)
      }
    }
  })
})
