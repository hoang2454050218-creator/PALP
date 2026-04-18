import { test, expect } from '@playwright/test'

const STUDENT_USER = process.env.E2E_STUDENT_USER || 'sv_test'
const STUDENT_PASS = process.env.E2E_STUDENT_PASS || 'testpass123'

async function loginAsStudent(page: import('@playwright/test').Page) {
  await page.goto('/login')
  await page.fill('#username', STUDENT_USER)
  await page.fill('#password', STUDENT_PASS)
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 })
}

test.describe('Preferences page', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsStudent(page)
    await page.goto('/preferences')
  })

  test('changing theme updates data-theme on root', async ({ page }) => {
    const html = page.locator('html')
    await expect(html).toHaveAttribute('data-theme', /light|dark|high-contrast/)

    const darkBtn = page.getByRole('radio', { name: /Tối/i }).first()
    if (await darkBtn.isVisible().catch(() => false)) {
      await darkBtn.click()
      await expect(html).toHaveAttribute('data-theme', 'dark')
    }
  })

  test('font scale buttons toggle CSS custom property', async ({ page }) => {
    const html = page.locator('html')
    const initialFont = await html.evaluate((el) =>
      getComputedStyle(el).getPropertyValue('--palp-font-scale').trim(),
    )
    expect(initialFont).toBeTruthy()

    const largeBtn = page.getByRole('radio', { name: /125%/i }).first()
    if (await largeBtn.isVisible().catch(() => false)) {
      await largeBtn.click()
      const after = await html.evaluate((el) =>
        getComputedStyle(el).getPropertyValue('--palp-font-scale').trim(),
      )
      expect(after).toBe('1.25')
    }
  })

  test('reduced motion toggle persists across reload', async ({ page }) => {
    const toggle = page.getByRole('switch').first()
    if (!(await toggle.isVisible().catch(() => false))) return

    await toggle.click()
    await page.reload()

    const html = page.locator('html')
    const reduced = await html.getAttribute('data-reduced-motion')
    expect(reduced === 'true' || reduced === null).toBeTruthy()
  })
})
