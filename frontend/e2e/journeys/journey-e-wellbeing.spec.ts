import { test, expect, type Page } from '@playwright/test'
import {
  loginViaApi,
  apiPost,
  apiGet,
  seedAssessmentCompletion,
} from '../helpers/api-helpers'

/**
 * Journey E — Wellbeing Nudge (J6 in QA_STANDARD)
 *
 * SV học liên tục > 50 phút → nudge hiện → SV respond → event tracking →
 * nudge history ghi nhận đúng.
 *
 * Gate:
 *   100% pass
 *   Ngưỡng 50 phút chính xác
 *   Nudge không block UI
 *   Response được lưu
 *   Event tracking hoạt động
 */

const STUDENT_USER = 'sv_test'
const STUDENT_PASS = 'testpass123'

test.describe.serial('Journey E — Wellbeing Nudge', () => {
  let page: Page

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage()
  })

  test.afterAll(async () => {
    await page.close()
  })

  test('E1: Login thành công', async () => {
    await page.goto('/login')
    await page.fill('#username', STUDENT_USER)
    await page.fill('#password', STUDENT_PASS)
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 })
  })

  test('E2: Wellbeing check — dưới 50 phút → should_nudge=false', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const res = await apiPost<any>(request, auth, '/wellbeing/check/', {
      continuous_minutes: 30,
    })

    expect(res.should_nudge).toBe(false)
  })

  test('E3: Wellbeing check — trên 50 phút → should_nudge=true', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const res = await apiPost<any>(request, auth, '/wellbeing/check/', {
      continuous_minutes: 55,
    })

    expect(res.should_nudge).toBe(true)
    expect(res.nudge).toBeTruthy()
    expect(res.nudge.nudge_type).toBeTruthy()
    expect(res.message).toBeTruthy()
  })

  test('E4: Wellbeing check — đúng ngưỡng 50 phút → should_nudge=true', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const res = await apiPost<any>(request, auth, '/wellbeing/check/', {
      continuous_minutes: 50,
    })

    expect(res.should_nudge).toBe(true)
  })

  test('E5: Nudge response — accept được lưu đúng', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const checkRes = await apiPost<any>(request, auth, '/wellbeing/check/', {
      continuous_minutes: 60,
    })

    expect(checkRes.should_nudge).toBe(true)
    const nudgeId = checkRes.nudge.id

    const respondRes = await apiPost<any>(
      request,
      auth,
      `/wellbeing/nudge/${nudgeId}/respond/`,
      { response: 'accepted' },
    )

    expect(respondRes.response).toBe('accepted')
    expect(respondRes.responded_at).toBeTruthy()
  })

  test('E6: Nudge response — dismiss được lưu đúng', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const checkRes = await apiPost<any>(request, auth, '/wellbeing/check/', {
      continuous_minutes: 55,
    })

    expect(checkRes.should_nudge).toBe(true)
    const nudgeId = checkRes.nudge.id

    const respondRes = await apiPost<any>(
      request,
      auth,
      `/wellbeing/nudge/${nudgeId}/respond/`,
      { response: 'dismissed' },
    )

    expect(respondRes.response).toBe('dismissed')
  })

  test('E7: Nudge history — xem được qua API', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const nudges = await apiGet<any[]>(request, auth, '/wellbeing/my/')
    const list = Array.isArray(nudges) ? nudges : (nudges as any).results ?? []

    expect(list.length).toBeGreaterThan(0)

    for (const nudge of list) {
      expect(nudge.nudge_type).toBeTruthy()
      expect(nudge.continuous_minutes).toBeGreaterThanOrEqual(50)
    }
  })

  test('E8: Nudge UI — không block flow học tập', async () => {
    await page.goto('/task')
    await page.waitForLoadState('networkidle')

    const taskPage = page.locator('text=Bài tập')
    const isTaskVisible = await taskPage.isVisible({ timeout: 10000 }).catch(() => false)

    const nudgeBanner = page.locator('[class*="nudge"], [data-testid="wellbeing-nudge"]')
    const isNudgeVisible = await nudgeBanner.isVisible({ timeout: 2000 }).catch(() => false)

    if (isNudgeVisible) {
      const taskStillVisible = await taskPage.isVisible().catch(() => false)
      expect(taskStillVisible).toBe(true)

      const dismissBtn = nudgeBanner.locator('button').first()
      if (await dismissBtn.isVisible().catch(() => false)) {
        await dismissBtn.click()
        await expect(taskPage).toBeVisible()
      }
    }

    expect(isTaskVisible).toBe(true)
  })

  test('E9: Gate — event tracking cho wellbeing', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const events = await apiGet<any>(request, auth, '/events/my/?event_name=wellbeing_nudge')
    const list = Array.isArray(events) ? events : (events as any).results ?? []

    test.info().annotations.push({
      type: 'wellbeing_events',
      description: `Wellbeing events tracked: ${list.length}`,
    })

    expect(list.length).toBeGreaterThan(0)
  })

  test('E10: Gate — acceptance rate trackable', async ({ request }) => {
    const auth = await loginViaApi(request, STUDENT_USER, STUDENT_PASS)

    const nudges = await apiGet<any[]>(request, auth, '/wellbeing/my/')
    const list = Array.isArray(nudges) ? nudges : (nudges as any).results ?? []

    const responded = list.filter(
      (n: any) => n.response === 'accepted' || n.response === 'dismissed',
    )
    const accepted = list.filter((n: any) => n.response === 'accepted')

    if (responded.length > 0) {
      const rate = accepted.length / responded.length
      test.info().annotations.push({
        type: 'acceptance_rate',
        description: `Acceptance rate: ${(rate * 100).toFixed(1)}% (${accepted.length}/${responded.length})`,
      })
    }

    expect(responded.length).toBeGreaterThan(0)
  })
})
