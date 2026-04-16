import { test, expect } from '@playwright/test'

test.describe('Student Wellbeing & Task', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('#username', 'sv_test')
    await page.fill('#password', 'testpass123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })
  })

  test('wellbeing nudge flow placeholder', async ({ page }) => {
    await page.goto('/task')

    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).not.toBeEmpty()

    test.info().annotations.push({
      type: 'info',
      description:
        'Full wellbeing nudge testing requires time simulation and BKT state seeding',
    })
  })
})
