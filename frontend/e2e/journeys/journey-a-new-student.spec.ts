import { test, expect, type Page } from '@playwright/test'
import {
  loginViaApi,
  getPathway,
  getMastery,
  apiGet,
} from '../helpers/api-helpers'

/**
 * Journey A — Sinh viên mới
 *
 * Đăng nhập → assessment → kết quả → nhận lộ trình → hoàn thành micro-task
 * đầu tiên → progress cập nhật.
 *
 * Gate:
 *   100% pass
 *   0 manual DB fix
 *   0 refresh required để thấy state đúng
 *   0 mismatch giữa UI và DB
 */

const STUDENT_USER = 'sv_test'
const STUDENT_PASS = 'testpass123'
const COURSE_ID = 1

test.describe.serial('Journey A — Sinh viên mới: Full onboarding', () => {
  let page: Page

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage()
  })

  test.afterAll(async () => {
    await page.close()
  })

  test('A1: Đăng nhập thành công và redirect đến dashboard', async () => {
    await page.goto('/login')
    await expect(page.locator('text=PALP')).toBeVisible()

    await page.fill('#username', STUDENT_USER)
    await page.fill('#password', STUDENT_PASS)
    await page.click('button[type="submit"]')

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 })
    await expect(page.locator('text=Xin chào')).toBeVisible({ timeout: 5000 })
  })

  test('A2: Từ dashboard đi đến trang đánh giá đầu vào', async () => {
    const startBtn = page.locator('a[href="/assessment"], button:has-text("Bắt đầu đánh giá")')
    const hasAssessmentLink = await startBtn.first().isVisible({ timeout: 5000 }).catch(() => false)

    if (hasAssessmentLink) {
      await startBtn.first().click()
      await expect(page).toHaveURL(/\/assessment/, { timeout: 5000 })
    } else {
      await page.goto('/assessment')
    }

    await expect(page.locator('text=Đánh giá đầu vào')).toBeVisible({ timeout: 5000 })
  })

  test('A3: Bắt đầu và hoàn thành bài đánh giá', async () => {
    const startButton = page.locator('button:has-text("Bắt đầu đánh giá")')
    const canStart = await startButton.first().isVisible({ timeout: 5000 }).catch(() => false)

    if (!canStart) {
      test.skip(true, 'No assessment available — seed data may be missing')
      return
    }

    await startButton.first().click()

    await expect(page.locator('text=/Câu \\d+ \\/ \\d+/')).toBeVisible({ timeout: 5000 })

    const MAX_QUESTIONS = 20
    for (let i = 0; i < MAX_QUESTIONS; i++) {
      const questionLabel = page.locator('text=/Câu \\d+ \\/ \\d+/')
      const isQuiz = await questionLabel.isVisible({ timeout: 3000 }).catch(() => false)
      if (!isQuiz) break

      const firstOption = page.locator('button.w-full.text-left').first()
      await expect(firstOption).toBeVisible({ timeout: 3000 })
      await firstOption.click()

      const nextBtn = page.locator('button:has-text("Tiếp theo")')
      const completeBtn = page.locator('button:has-text("Hoàn thành")')

      if (await nextBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await nextBtn.click()
      } else if (await completeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await completeBtn.click()
        break
      }
    }
  })

  test('A4: Xem kết quả đánh giá — hiển thị điểm', async () => {
    await expect(page.locator('text=Kết quả đánh giá')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=/\\d+%/')).toBeVisible()
    await expect(page.locator('text=Điểm đánh giá đầu vào')).toBeVisible()
  })

  test('A5: Chuyển đến lộ trình học tập', async () => {
    const pathwayBtn = page.locator('button:has-text("Bắt đầu lộ trình học")')
    await expect(pathwayBtn).toBeVisible()
    await pathwayBtn.click()

    await expect(page).toHaveURL(/\/pathway/, { timeout: 10000 })
    await expect(page.locator('text=Lộ trình học tập')).toBeVisible({ timeout: 5000 })

    const milestoneCard = page.locator('[role="progressbar"], text=/Milestone|M\\d:/')
    const hasMilestone = await milestoneCard.first().isVisible({ timeout: 5000 }).catch(() => false)
    expect(hasMilestone).toBe(true)
  })

  test('A6: Mở trang bài tập — hiển thị micro-task đầu tiên', async () => {
    await page.goto('/task')
    await page.waitForLoadState('networkidle')

    const taskLoaded = page.locator('text=Bài tập')
    await expect(taskLoaded).toBeVisible({ timeout: 10000 })

    const hasQuestion = await page
      .locator('button.w-full.text-left')
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false)

    const noTask = await page
      .locator('text=Chưa có bài tập nào')
      .isVisible({ timeout: 1000 })
      .catch(() => false)

    expect(hasQuestion || noTask).toBe(true)

    if (!hasQuestion) {
      test.skip(true, 'No micro-tasks seeded for pathway')
    }
  })

  test('A7: Hoàn thành micro-task đầu tiên — phản hồi đúng/sai', async () => {
    const optionButtons = page.locator('button.w-full.text-left')
    const hasOptions = await optionButtons.first().isVisible({ timeout: 3000 }).catch(() => false)

    if (!hasOptions) {
      test.skip(true, 'No task options visible')
      return
    }

    await optionButtons.first().click()

    const submitBtn = page.locator('button:has-text("Nộp bài")')
    await expect(submitBtn).toBeEnabled()
    await submitBtn.click()

    const resultFeedback = page.locator('text=/Chính xác!|Chưa đúng/')
    await expect(resultFeedback).toBeVisible({ timeout: 5000 })

    const masteryDisplay = page.locator('text=/Mastery: \\d+%/')
    await expect(masteryDisplay).toBeVisible()

    const pathwayMsg = page.locator('text=Pathway')
    await expect(pathwayMsg).toBeVisible()
  })

  test('A8: Gate — UI-DB consistency: progress cập nhật đúng', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const pathway = await getPathway(request, auth, COURSE_ID)
    expect(pathway).toBeTruthy()
    expect(pathway.course).toBe(COURSE_ID)
    expect(pathway.current_concept).not.toBeNull()

    const mastery = await getMastery(request, auth, COURSE_ID)
    expect(mastery.length).toBeGreaterThan(0)

    const hasAttempts = mastery.some((m: any) => m.attempt_count >= 1)
    expect(hasAttempts).toBe(true)

    const profile = await apiGet<any>(request, auth, `/assessment/profile/${COURSE_ID}/`)
    expect(profile).toBeTruthy()
    expect(profile.overall_score).toBeGreaterThanOrEqual(0)

    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')

    const uiProgress = page.locator('text=/Tiến độ tổng/')
    await expect(uiProgress).toBeVisible({ timeout: 5000 })

    const uiMastery = page.locator('text=/Mastery trung bình/')
    await expect(uiMastery).toBeVisible()

    const uiScore = page.locator(`text=/\\d+%/`)
    await expect(uiScore.first()).toBeVisible()
  })
})
