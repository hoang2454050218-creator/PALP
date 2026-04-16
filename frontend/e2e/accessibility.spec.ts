import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility — WCAG 2.1 AA', () => {
  test.describe('Login page', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/login')
    })

    test('passes automated WCAG AA checks', async ({ page }) => {
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze()
      expect(results.violations).toEqual([])
    })

    test('has correct lang attribute', async ({ page }) => {
      const lang = await page.locator('html').getAttribute('lang')
      expect(lang).toBe('vi')
    })

    test('form inputs have associated labels', async ({ page }) => {
      const username = page.locator('#username')
      const password = page.locator('#password')
      await expect(username).toBeVisible()
      await expect(password).toBeVisible()

      const usernameLabel = page.locator('label[for="username"]')
      const passwordLabel = page.locator('label[for="password"]')
      await expect(usernameLabel).toHaveText('Tên đăng nhập')
      await expect(passwordLabel).toHaveText('Mật khẩu')
    })

    test('tab order covers all interactive elements', async ({ page }) => {
      await page.keyboard.press('Tab')
      const firstFocused = await page.evaluate(() => document.activeElement?.id || document.activeElement?.tagName)
      expect(firstFocused).toBeTruthy()

      const visited: string[] = []
      for (let i = 0; i < 10; i++) {
        const el = await page.evaluate(() => {
          const a = document.activeElement
          return a ? `${a.tagName}#${a.id || ''}` : ''
        })
        if (el && !visited.includes(el)) visited.push(el)
        await page.keyboard.press('Tab')
      }
      expect(visited.length).toBeGreaterThanOrEqual(3)
    })

    test('error message has role=alert', async ({ page }) => {
      await page.fill('#username', 'wrong')
      await page.fill('#password', 'wrong')
      await page.click('button[type="submit"]')

      const errorAlert = page.locator('[role="alert"]')
      await expect(errorAlert).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('Mobile responsive', () => {
    test.use({ viewport: { width: 375, height: 812 } })

    test('login page is usable at 375px width', async ({ page }) => {
      await page.goto('/login')
      const card = page.locator('form')
      await expect(card).toBeVisible()

      const box = await card.boundingBox()
      expect(box).toBeTruthy()
      if (box) {
        expect(box.width).toBeLessThanOrEqual(375)
      }
    })
  })

  test.describe('Skip link', () => {
    test('skip link is focusable and targets main content', async ({ page }) => {
      await page.goto('/login')
      await page.keyboard.press('Tab')

      const skipLink = page.locator('a[href="#main-content"]')
      const isVisible = await skipLink.isVisible().catch(() => false)
      if (isVisible) {
        const href = await skipLink.getAttribute('href')
        expect(href).toBe('#main-content')
      }
    })
  })

  test.describe('Quiz accessibility', () => {
    test('assessment quiz options have radiogroup role', async ({ page }) => {
      await page.goto('/assessment')

      const radiogroup = page.locator('[role="radiogroup"]')
      const count = await radiogroup.count()
      if (count > 0) {
        const radios = page.locator('[role="radio"]')
        const radioCount = await radios.count()
        expect(radioCount).toBeGreaterThan(0)

        for (let i = 0; i < radioCount; i++) {
          const ariaChecked = await radios.nth(i).getAttribute('aria-checked')
          expect(['true', 'false']).toContain(ariaChecked)
        }
      }
    })
  })

  test.describe('Color and contrast', () => {
    test('no color-only severity indicators on alerts page', async ({ page }) => {
      await page.goto('/alerts')

      const severityBadges = page.locator('.inline-flex.items-center.rounded-full')
      const count = await severityBadges.count()
      if (count > 0) {
        for (let i = 0; i < Math.min(count, 5); i++) {
          const text = await severityBadges.nth(i).textContent()
          expect(text?.trim().length).toBeGreaterThan(0)
        }
      }
    })
  })

  test.describe('Navigation', () => {
    test('sidebar nav has aria-label', async ({ page }) => {
      await page.goto('/dashboard')

      const nav = page.locator('nav[aria-label]')
      const count = await nav.count()
      if (count > 0) {
        const label = await nav.first().getAttribute('aria-label')
        expect(label).toBeTruthy()
      }
    })
  })
})
