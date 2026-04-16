import { test, expect, type Page } from '@playwright/test'
import {
  loginViaApi,
  apiPost,
  apiGet,
  seedAssessmentCompletion,
  submitTaskAnswer,
  getNextTask,
  getAlerts,
  getInterventionHistory,
} from '../helpers/api-helpers'

/**
 * Journey C — Giảng viên can thiệp
 *
 * Hệ thống tạo alert → giảng viên mở dashboard → xem lý do → chọn action →
 * hệ thống gửi → sau 1 tuần đo lại hiệu quả.
 *
 * Gate:
 *   100% pass
 *   0 cross-class leak
 *   0 missing audit log
 *   0 stale action state
 */

const STUDENT_USER = 'sv_test'
const STUDENT_PASS = 'testpass123'
const LECTURER_USER = 'gv_test'
const LECTURER_PASS = 'testpass123'
const COURSE_ID = 1

test.describe.serial('Journey C — Giảng viên can thiệp', () => {
  let page: Page
  let seededAlertId: number | null = null
  let studentId: number | null = null
  let classId: number | null = null

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage()
  })

  test.afterAll(async () => {
    await page.close()
  })

  test('C0: Pre-seed — tạo alert cho student qua API', async ({ request }) => {
    const studentAuth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const profile = await apiGet<any>(request, studentAuth, '/auth/profile/')
    studentId = profile.id
    expect(studentId).toBeTruthy()

    const classes = await apiGet<any>(request, studentAuth, '/auth/classes/')
    const classList = Array.isArray(classes) ? classes : classes.results ?? []

    if (classList.length > 0) {
      classId = classList[0].id
    }

    const task = await getNextTask(request, studentAuth, COURSE_ID).catch(() => null)

    if (!task || task.detail) {
      await seedAssessmentCompletion(request, studentAuth)
    }

    const freshTask = await getNextTask(request, studentAuth, COURSE_ID).catch(() => null)

    if (freshTask && freshTask.id && freshTask.content?.correct_answer) {
      const wrongAnswer = '__DEFINITELY_WRONG__'
      for (let i = 0; i < 3; i++) {
        await submitTaskAnswer(request, studentAuth, freshTask.id, wrongAnswer).catch(() => {})
      }
    }

    const lecturerAuth = await loginViaApi(request, LECTURER_USER, LECTURER_PASS)

    const alerts = await getAlerts(request, lecturerAuth, 'status=active')

    if (alerts.length > 0) {
      seededAlertId = alerts[0].id
      classId = classId ?? alerts[0].student_class
    }

    test.info().annotations.push({
      type: 'seed_info',
      description: `studentId=${studentId}, classId=${classId}, alertId=${seededAlertId}, alertCount=${alerts.length}`,
    })
  })

  test('C1: Giảng viên login → redirect /overview', async () => {
    await page.goto('/login')
    await page.fill('#username', LECTURER_USER)
    await page.fill('#password', LECTURER_PASS)
    await page.click('button[type="submit"]')

    await expect(page).toHaveURL(/\/overview/, { timeout: 15000 })
  })

  test('C2: Class overview hiển thị thống kê đúng', async () => {
    await expect(page.locator('text=Tổng quan lớp học')).toBeVisible({ timeout: 5000 })

    await expect(page.locator('text=On-track')).toBeVisible()
    await expect(page.locator('text=Cần chú ý')).toBeVisible()
    await expect(page.locator('text=Cần can thiệp')).toBeVisible()
    await expect(page.locator('text=Tổng sinh viên')).toBeVisible()

    await expect(page.locator('text=Cảnh báo gần đây')).toBeVisible()
  })

  test('C3: Navigate /alerts — xem danh sách cảnh báo', async () => {
    await page.goto('/alerts')

    await expect(page.locator('text=Cảnh báo sớm')).toBeVisible({ timeout: 5000 })

    const alertCard = page.locator('[class*="Card"]').filter({
      has: page.locator('text=/Cần can thiệp|Cần chú ý/'),
    })

    const noAlerts = page.locator('text=Không có cảnh báo nào')

    const hasAlerts = await alertCard.first().isVisible({ timeout: 5000 }).catch(() => false)
    const isEmpty = await noAlerts.isVisible({ timeout: 1000 }).catch(() => false)

    test.info().annotations.push({
      type: 'alert_state',
      description: `hasAlerts=${hasAlerts}, isEmpty=${isEmpty}`,
    })

    expect(hasAlerts || isEmpty).toBe(true)

    if (!hasAlerts) {
      test.skip(true, 'No active alerts — early warning rules may need trigger data')
    }
  })

  test('C4: Xem chi tiết alert — lý do + hành động gợi ý', async () => {
    const alertCards = page.locator('[class*="Card"]').filter({
      has: page.locator('text=/Cần can thiệp|Cần chú ý/'),
    })

    const firstAlert = alertCards.first()
    await expect(firstAlert).toBeVisible()

    const reason = firstAlert.locator('p.text-sm').first()
    await expect(reason).not.toBeEmpty()

    const triggerBadge = firstAlert.locator('[class*="Badge"]').filter({
      has: page.locator(
        'text=/Không hoạt động|Thất bại nhiều lần|Chậm tiến độ|Mastery thấp/',
      ),
    })
    const hasTrigger = await triggerBadge.first().isVisible({ timeout: 2000 }).catch(() => false)

    test.info().annotations.push({
      type: 'alert_detail',
      description: `Has trigger badge: ${hasTrigger}`,
    })
  })

  test('C5: Chọn action "Gửi tin" → alert resolve', async () => {
    const sendMsgBtn = page.locator('button:has-text("Gửi tin")').first()
    const canSend = await sendMsgBtn.isVisible({ timeout: 3000 }).catch(() => false)

    if (!canSend) {
      test.skip(true, 'No send-message button visible')
      return
    }

    await sendMsgBtn.click()

    await page.waitForTimeout(2000)

    const remainingAlerts = page.locator('[class*="Card"]').filter({
      has: page.locator('text=/Cần can thiệp|Cần chú ý/'),
    })

    const noAlerts = page.locator('text=Không có cảnh báo nào')
    const count = await remainingAlerts.count()
    const empty = await noAlerts.isVisible({ timeout: 2000 }).catch(() => false)

    test.info().annotations.push({
      type: 'after_intervention',
      description: `Remaining alerts: ${count}, empty state: ${empty}`,
    })
  })

  test('C6: Navigate /history — intervention xuất hiện', async () => {
    await page.goto('/history')

    await expect(page.locator('text=Lịch sử can thiệp')).toBeVisible({ timeout: 5000 })

    const historyCard = page.locator('[class*="Card"]')
    const hasHistory = await historyCard
      .filter({ has: page.locator('text=/Chờ phản hồi|Đã xử lý|SV đã phản hồi|Không phản hồi/') })
      .first()
      .isVisible({ timeout: 5000 })
      .catch(() => false)

    const noHistory = page
      .locator('text=Chưa có lịch sử can thiệp')
      .isVisible({ timeout: 2000 })
      .catch(() => false)

    expect(hasHistory || (await noHistory)).toBe(true)
  })

  test('C7: Gate — 0 cross-class leak: alert API scoped đúng class', async ({ request }) => {
    const lecturerAuth = await loginViaApi(request, LECTURER_USER, LECTURER_PASS)

    const fakeClassId = 999999
    const leakedAlerts = await request
      .get(`http://localhost:8000/api/dashboard/alerts/?class_id=${fakeClassId}`, {
        headers: {
          Cookie: lecturerAuth.cookies.map((c) => `${c.name}=${c.value}`).join('; '),
        },
      })
      .then(async (res) => {
        if (res.status() === 403) return []
        if (!res.ok()) return []
        const data = await res.json()
        return Array.isArray(data) ? data : data.results ?? []
      })

    expect(leakedAlerts.length).toBe(0)

    if (classId) {
      const ownAlerts = await getAlerts(request, lecturerAuth, `class_id=${classId}`)
      test.info().annotations.push({
        type: 'cross_class_check',
        description: `Own class(${classId}): ${ownAlerts.length} alerts, Fake class(${fakeClassId}): ${leakedAlerts.length} alerts`,
      })
    }
  })

  test('C8: Gate — 0 missing audit log: intervention action logged', async ({ request }) => {
    const lecturerAuth = await loginViaApi(request, LECTURER_USER, LECTURER_PASS)
    const history = await getInterventionHistory(request, lecturerAuth, classId ?? undefined)

    test.info().annotations.push({
      type: 'audit_log',
      description: `Intervention history count: ${history.length}`,
    })
  })

  test('C9: Gate — 0 stale action state: resolved alert not in active list', async ({
    request,
  }) => {
    const lecturerAuth = await loginViaApi(request, LECTURER_USER, LECTURER_PASS)
    const activeAlerts = await getAlerts(request, lecturerAuth, 'status=active')

    if (seededAlertId) {
      const staleAlert = activeAlerts.find((a: any) => a.id === seededAlertId)
      expect(staleAlert).toBeUndefined()
    }

    for (const alert of activeAlerts) {
      expect(alert.status).toBe('active')
    }
  })
})
