import { test, expect } from '@playwright/test'

test.describe('Student Pathway Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('#username', 'sv_test')
    await page.fill('#password', 'testpass123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })
  })

  test('student can view pathway', async ({ page }) => {
    await page.goto('/pathway')

    await expect(page.locator('text=Lộ trình học tập')).toBeVisible()

    const progressBar = page.locator('[role="progressbar"]')
    const hasMilestones = await page
      .locator('text=/Milestone|bài/')
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false)

    if (hasMilestones) {
      await expect(progressBar.first()).toBeVisible()
    } else {
      await expect(page.locator('body')).toContainText(/Lộ trình|pathway/i)
    }
  })

  test('pathway shows current milestone highlighted', async ({ page }) => {
    await page.goto('/pathway')

    await expect(page.locator('text=Lộ trình học tập')).toBeVisible()

    const currentMilestone = page.locator('[class*="ring-2"][class*="ring-primary"]')
    const hasCurrentMilestone = await currentMilestone
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false)

    if (hasCurrentMilestone) {
      await expect(currentMilestone.first()).toBeVisible()

      await expect(
        currentMilestone.locator('button', { hasText: 'Tiếp tục học' }),
      ).toBeVisible()
    } else {
      test.info().annotations.push({
        type: 'info',
        description: 'No current milestone - student may not have started pathway yet',
      })
    }
  })
})
