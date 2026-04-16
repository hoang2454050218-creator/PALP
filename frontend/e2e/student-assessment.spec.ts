import { test, expect } from '@playwright/test'

test.describe('Student Assessment Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('#username', 'sv_test')
    await page.fill('#password', 'testpass123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })
  })

  test('student can view available assessments', async ({ page }) => {
    await page.goto('/assessment')

    await expect(page.locator('text=Đánh giá đầu vào')).toBeVisible()

    const hasAssessmentCards = await page
      .locator('[class*="Card"], [data-testid="assessment-card"]')
      .first()
      .isVisible()
      .catch(() => false)

    if (hasAssessmentCards) {
      await expect(
        page.locator('button', { hasText: 'Bắt đầu đánh giá' }).first(),
      ).toBeVisible()
    } else {
      await expect(
        page.locator('text=Chưa có bài đánh giá nào'),
      ).toBeVisible()
    }
  })

  test('student can complete full assessment', async ({ page }) => {
    await page.goto('/assessment')

    const startButton = page.locator('button', {
      hasText: 'Bắt đầu đánh giá',
    })
    const canStart = await startButton
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false)

    if (!canStart) {
      test.skip(true, 'No assessments available to start')
      return
    }

    await startButton.first().click()

    await expect(page.locator('text=/Câu \\d+ \\/ \\d+/')).toBeVisible({
      timeout: 5000,
    })

    let hasMoreQuestions = true
    while (hasMoreQuestions) {
      const optionButton = page
        .locator('button.w-full.text-left', { hasText: /^A\./ })
        .first()
      const optionVisible = await optionButton
        .isVisible({ timeout: 3000 })
        .catch(() => false)

      if (!optionVisible) break

      await optionButton.click()

      const nextButton = page.locator('button', { hasText: 'Tiếp theo' })
      const completeButton = page.locator('button', { hasText: 'Hoàn thành' })

      if (await nextButton.isVisible().catch(() => false)) {
        await nextButton.click()
      } else if (await completeButton.isVisible().catch(() => false)) {
        await completeButton.click()
        hasMoreQuestions = false
      } else {
        break
      }
    }

    await expect(page.locator('text=Kết quả đánh giá')).toBeVisible({
      timeout: 10000,
    })
    await expect(page.locator('text=/\\d+%/')).toBeVisible()
  })
})
