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

test.describe('Student Wellbeing UI', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsStudent(page)
  })

  test('renders wellbeing page with summary cards and history', async ({ page }) => {
    await page.goto('/wellbeing')
    await expect(page.getByRole('heading', { name: /Sức khỏe học tập/i })).toBeVisible()

    // Summary cards (4 of them)
    await expect(page.getByText(/Tổng lời nhắc/i)).toBeVisible()
    await expect(page.getByText(/Đã chấp nhận nghỉ/i)).toBeVisible()
    await expect(page.getByText(/Đã bỏ qua/i)).toBeVisible()
    await expect(page.getByText(/Đang chờ phản hồi/i)).toBeVisible()

    // Either history list or empty state must render
    const hasList = await page
      .getByRole('list', { name: /Danh sách lời nhắc sức khỏe/i })
      .count()
    const hasEmpty = await page.getByText(/Chưa có lời nhắc nào/i).count()
    expect(hasList + hasEmpty).toBeGreaterThan(0)
  })

  test('refresh button reloads data without page reload', async ({ page }) => {
    await page.goto('/wellbeing')
    const refresh = page.getByRole('button', { name: /Làm mới/i })
    await expect(refresh).toBeVisible()

    await refresh.click()
    // Page should not have full reload — sidebar still visible.
    await expect(page.getByRole('navigation', { name: /Điều hướng chính/i })).toBeVisible()
  })

  test('sidebar exposes wellbeing entry', async ({ page }) => {
    await page.goto('/dashboard')
    const link = page.getByRole('link', { name: /Sức khỏe học tập/i })
    await expect(link).toBeVisible()
    await link.click()
    await expect(page).toHaveURL(/\/wellbeing/)
  })
})
