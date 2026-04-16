import { test, expect } from '@playwright/test'

test.describe('Lecturer Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('#username', 'gv_test')
    await page.fill('#password', 'testpass123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/overview/, { timeout: 10000 })
  })

  test('lecturer can view class overview', async ({ page }) => {
    await expect(page.locator('text=Tổng quan lớp học')).toBeVisible()

    await expect(page.locator('text=On-track')).toBeVisible()
    await expect(page.locator('text=Cần chú ý')).toBeVisible()
    await expect(page.locator('text=Cần can thiệp')).toBeVisible()
    await expect(page.locator('text=Tổng sinh viên')).toBeVisible()

    await expect(page.locator('text=Sức khỏe cohort')).toBeVisible()
    await expect(page.locator('text=Cảnh báo gần đây')).toBeVisible()
  })

  test('lecturer can view alerts', async ({ page }) => {
    await page.goto('/alerts')

    await expect(page.locator('text=Cảnh báo sớm')).toBeVisible()

    const hasAlerts = await page
      .locator('text=Cần can thiệp')
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false)

    if (hasAlerts) {
      await expect(
        page.locator('button', { hasText: /Tất cả/ }),
      ).toBeVisible()
    } else {
      await expect(
        page.locator('text=Không có cảnh báo nào'),
      ).toBeVisible()
    }
  })

  test('lecturer can view intervention history', async ({ page }) => {
    await page.goto('/history')

    await expect(page.locator('text=Lịch sử can thiệp')).toBeVisible()

    const hasHistory = await page
      .locator('[class*="Card"]')
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false)

    if (hasHistory) {
      await expect(page.locator('body')).toContainText(
        /Chờ phản hồi|Đã xử lý|SV đã phản hồi|Không phản hồi|Chưa có lịch sử/,
      )
    } else {
      await expect(
        page.locator('text=Chưa có lịch sử can thiệp'),
      ).toBeVisible()
    }
  })
})
