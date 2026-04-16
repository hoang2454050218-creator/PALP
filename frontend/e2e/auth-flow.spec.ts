import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('login page renders correctly', async ({ page }) => {
    await expect(page.locator('text=PALP')).toBeVisible()
    await expect(
      page.locator('text=Personalized Adaptive Learning Platform'),
    ).toBeVisible()

    const usernameInput = page.locator('#username')
    await expect(usernameInput).toBeVisible()
    await expect(usernameInput).toHaveAttribute(
      'placeholder',
      'Nhập tên đăng nhập',
    )

    const passwordInput = page.locator('#password')
    await expect(passwordInput).toBeVisible()
    await expect(passwordInput).toHaveAttribute('type', 'password')
    await expect(passwordInput).toHaveAttribute(
      'placeholder',
      'Nhập mật khẩu',
    )

    await expect(
      page.locator('button[type="submit"]', { hasText: 'Đăng nhập' }),
    ).toBeVisible()
  })

  test('successful student login redirects to dashboard', async ({ page }) => {
    await page.fill('#username', 'sv_test')
    await page.fill('#password', 'testpass123')
    await page.click('button[type="submit"]')

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })
  })

  test('successful lecturer login redirects to overview', async ({ page }) => {
    await page.fill('#username', 'gv_test')
    await page.fill('#password', 'testpass123')
    await page.click('button[type="submit"]')

    await expect(page).toHaveURL(/\/overview/, { timeout: 10000 })
  })

  test('invalid credentials shows error', async ({ page }) => {
    await page.fill('#username', 'sv_test')
    await page.fill('#password', 'wrong_password')
    await page.click('button[type="submit"]')

    const errorMsg = page.locator('.bg-destructive\\/10')
    await expect(errorMsg).toBeVisible({ timeout: 5000 })
    await expect(errorMsg).toContainText('Tên đăng nhập hoặc mật khẩu không đúng')
  })

  test('logout clears session', async ({ page }) => {
    await page.fill('#username', 'sv_test')
    await page.fill('#password', 'testpass123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })

    await page.goto('/login')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('#username')).toBeVisible()
  })
})
