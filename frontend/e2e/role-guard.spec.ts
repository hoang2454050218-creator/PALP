import { test, expect } from '@playwright/test'

const STUDENT_USER = process.env.E2E_STUDENT_USER || 'sv_test'
const STUDENT_PASS = process.env.E2E_STUDENT_PASS || 'testpass123'
const LECTURER_USER = process.env.E2E_LECTURER_USER || 'lec_test'
const LECTURER_PASS = process.env.E2E_LECTURER_PASS || 'testpass123'

async function login(page: import('@playwright/test').Page, user: string, pass: string) {
  await page.goto('/login')
  await page.fill('#username', user)
  await page.fill('#password', pass)
  await page.click('button[type="submit"]')
}

test.describe('Role guard', () => {
  test('student is redirected away from lecturer overview', async ({ page }) => {
    await login(page, STUDENT_USER, STUDENT_PASS)
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 })

    await page.goto('/overview')
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 })
  })

  test('lecturer is redirected away from student dashboard', async ({ page }) => {
    await login(page, LECTURER_USER, LECTURER_PASS)
    await expect(page).toHaveURL(/\/overview/, { timeout: 15000 })

    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/overview/, { timeout: 10000 })
  })

  test('unauthenticated user lands on /login from any protected route', async ({ page }) => {
    await page.context().clearCookies()
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
  })
})
