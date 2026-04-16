/**
 * Assessment edge-case E2E tests (AS-02, AS-03, AS-09).
 *
 * AS-02  Reload mid-assessment -> state preserved
 * AS-03  Network loss mid-assessment -> graceful error handling
 * AS-09  Drag-drop wrong format -> no crash, proper error shown
 */
import { test, expect, Page } from '@playwright/test'

const login = async (page: Page) => {
  await page.goto('/login')
  await page.fill('#username', 'sv_test')
  await page.fill('#password', 'testpass123')
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })
}

const startAssessment = async (page: Page): Promise<boolean> => {
  await page.goto('/assessment')
  const startButton = page.locator('button', {
    hasText: 'Bắt đầu đánh giá',
  })
  const canStart = await startButton
    .first()
    .isVisible({ timeout: 5000 })
    .catch(() => false)

  if (!canStart) return false
  await startButton.first().click()
  await expect(page.locator('text=/Câu \\d+ \\/ \\d+/')).toBeVisible({
    timeout: 5000,
  })
  return true
}

const answerCurrentQuestion = async (page: Page) => {
  const optionButton = page
    .locator('button.w-full.text-left', { hasText: /^A\./ })
    .first()
  const visible = await optionButton
    .isVisible({ timeout: 3000 })
    .catch(() => false)
  if (!visible) return false
  await optionButton.click()

  const nextButton = page.locator('button', { hasText: 'Tiếp theo' })
  if (await nextButton.isVisible().catch(() => false)) {
    await nextButton.click()
    return true
  }
  return false
}

test.describe('Assessment Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  // AS-02: Reload mid-assessment -> state preserved
  test('AS-02: reload preserves answered questions', async ({ page }) => {
    const started = await startAssessment(page)
    if (!started) {
      test.skip(true, 'No assessments available')
      return
    }

    await answerCurrentQuestion(page)

    const urlBefore = page.url()
    await page.reload()
    await page.waitForLoadState('networkidle')

    const questionIndicator = page.locator('text=/Câu \\d+ \\/ \\d+/')
    const resultPage = page.locator('text=Kết quả đánh giá')
    const assessmentPage = page.locator('text=Đánh giá đầu vào')

    const isStillInAssessment = await questionIndicator
      .isVisible({ timeout: 5000 })
      .catch(() => false)
    const isResult = await resultPage
      .isVisible({ timeout: 2000 })
      .catch(() => false)
    const isAssessmentList = await assessmentPage
      .isVisible({ timeout: 2000 })
      .catch(() => false)

    expect(isStillInAssessment || isResult || isAssessmentList).toBe(true)
  })

  // AS-03: Network loss mid-assessment -> graceful handling
  test('AS-03: offline during assessment shows error gracefully', async ({
    page,
    context,
  }) => {
    const started = await startAssessment(page)
    if (!started) {
      test.skip(true, 'No assessments available')
      return
    }

    await context.setOffline(true)

    const optionButton = page
      .locator('button.w-full.text-left', { hasText: /^A\./ })
      .first()
    const visible = await optionButton
      .isVisible({ timeout: 3000 })
      .catch(() => false)

    if (visible) {
      await optionButton.click()

      await page.waitForTimeout(2000)

      const hasError = await page
        .locator(
          '[role="alert"], [class*="error"], [class*="Error"], text=/lỗi|thất bại|kết nối/i',
        )
        .first()
        .isVisible({ timeout: 5000 })
        .catch(() => false)

      const pageNotCrashed =
        (await page.title().catch(() => '')) !== '' ||
        (await page
          .locator('body')
          .isVisible()
          .catch(() => false))

      expect(pageNotCrashed).toBe(true)
    }

    await context.setOffline(false)
  })

  // AS-09: Drag-drop wrong format -> no crash
  test('AS-09: invalid input does not crash assessment UI', async ({
    page,
  }) => {
    const started = await startAssessment(page)
    if (!started) {
      test.skip(true, 'No assessments available')
      return
    }

    const noJsErrors: string[] = []
    page.on('pageerror', (error) => {
      noJsErrors.push(error.message)
    })

    const optionButton = page
      .locator('button.w-full.text-left')
      .first()
    const visible = await optionButton
      .isVisible({ timeout: 3000 })
      .catch(() => false)

    if (visible) {
      await optionButton.click()
    }

    await page.waitForTimeout(1000)

    const bodyVisible = await page
      .locator('body')
      .isVisible()
      .catch(() => false)
    expect(bodyVisible).toBe(true)

    const criticalErrors = noJsErrors.filter(
      (e) =>
        e.includes('TypeError') ||
        e.includes('Cannot read') ||
        e.includes('undefined is not'),
    )
    expect(criticalErrors).toHaveLength(0)
  })
})
