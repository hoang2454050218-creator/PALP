import { type APIRequestContext } from '@playwright/test'

const API_BASE = 'http://localhost:8000/api'

interface AuthCookies {
  cookies: { name: string; value: string }[]
}

export async function loginViaApi(
  request: APIRequestContext,
  username: string,
  password: string,
): Promise<AuthCookies> {
  const res = await request.post(`${API_BASE}/auth/login/`, {
    data: { username, password },
  })

  if (!res.ok()) {
    throw new Error(`Login failed for ${username}: ${res.status()}`)
  }

  const setCookies = res.headersArray().filter((h) => h.name.toLowerCase() === 'set-cookie')
  const cookies = setCookies.map((h) => {
    const [pair] = h.value.split(';')
    const [name, ...rest] = pair.split('=')
    return { name: name.trim(), value: rest.join('=').trim() }
  })

  return { cookies }
}

function cookieHeader(auth: AuthCookies): string {
  return auth.cookies.map((c) => `${c.name}=${c.value}`).join('; ')
}

export function apiGet<T = unknown>(
  request: APIRequestContext,
  auth: AuthCookies,
  endpoint: string,
): Promise<T> {
  return request
    .get(`${API_BASE}${endpoint}`, {
      headers: { Cookie: cookieHeader(auth) },
    })
    .then(async (res) => {
      if (!res.ok()) throw new Error(`GET ${endpoint} -> ${res.status()}`)
      return res.json() as T
    })
}

export function apiPost<T = unknown>(
  request: APIRequestContext,
  auth: AuthCookies,
  endpoint: string,
  data?: unknown,
): Promise<T> {
  return request
    .post(`${API_BASE}${endpoint}`, {
      headers: {
        Cookie: cookieHeader(auth),
        'Content-Type': 'application/json',
      },
      data,
    })
    .then(async (res) => {
      if (!res.ok()) {
        const body = await res.text().catch(() => '')
        throw new Error(`POST ${endpoint} -> ${res.status()} ${body}`)
      }
      return res.json() as T
    })
}

export async function seedAssessmentCompletion(
  request: APIRequestContext,
  auth: AuthCookies,
): Promise<{ sessionId: number; profileScore: number }> {
  const assessments = await apiGet<any[]>(request, auth, '/assessment/')
  const list = Array.isArray(assessments) ? assessments : (assessments as any).results ?? []
  if (list.length === 0) throw new Error('No assessments available')

  const assessment = list[0]
  const startRes = await apiPost<any>(request, auth, `/assessment/${assessment.id}/start/`)
  const sessionId: number = startRes.id

  const questionsRaw = await apiGet<any>(request, auth, `/assessment/${assessment.id}/questions/`)
  const questions = Array.isArray(questionsRaw)
    ? questionsRaw
    : questionsRaw.results ?? []

  for (const q of questions) {
    await apiPost(request, auth, `/assessment/sessions/${sessionId}/answer/`, {
      question_id: q.id,
      answer: q.options?.[0] ?? 'A',
      time_taken_seconds: 10,
    })
  }

  const completeRes = await apiPost<any>(
    request,
    auth,
    `/assessment/sessions/${sessionId}/complete/`,
  )

  return {
    sessionId,
    profileScore: completeRes.profile?.overall_score ?? 0,
  }
}

export async function submitTaskAnswer(
  request: APIRequestContext,
  auth: AuthCookies,
  taskId: number,
  answer: string,
): Promise<{
  attempt: { is_correct: boolean; attempt_number: number }
  mastery: { p_mastery: number; attempt_count: number }
  pathway: { action: string; p_mastery: number; supplementary_content?: unknown }
}> {
  return apiPost(request, auth, '/adaptive/submit/', {
    task_id: taskId,
    answer,
    duration_seconds: 30,
    hints_used: 0,
  })
}

export async function getNextTask(
  request: APIRequestContext,
  auth: AuthCookies,
  courseId = 1,
): Promise<any> {
  return apiGet(request, auth, `/adaptive/next-task/${courseId}/`)
}

export async function getPathway(
  request: APIRequestContext,
  auth: AuthCookies,
  courseId = 1,
): Promise<any> {
  return apiGet(request, auth, `/adaptive/pathway/${courseId}/`)
}

export async function getMastery(
  request: APIRequestContext,
  auth: AuthCookies,
  courseId = 1,
): Promise<any[]> {
  const res = await apiGet<any>(request, auth, `/adaptive/mastery/?course=${courseId}`)
  return Array.isArray(res) ? res : res.results ?? []
}

export async function getAlerts(
  request: APIRequestContext,
  auth: AuthCookies,
  params = '',
): Promise<any[]> {
  const res = await apiGet<any>(request, auth, `/dashboard/alerts/${params ? '?' + params : ''}`)
  return Array.isArray(res) ? res : res.results ?? []
}

export async function getInterventionHistory(
  request: APIRequestContext,
  auth: AuthCookies,
  classId?: number,
): Promise<any[]> {
  const qs = classId ? `?class_id=${classId}` : ''
  const res = await apiGet<any>(request, auth, `/dashboard/interventions/history/${qs}`)
  return Array.isArray(res) ? res : res.results ?? []
}

export async function getAuditLog(
  request: APIRequestContext,
  auth: AuthCookies,
): Promise<any[]> {
  const res = await apiGet<any>(request, auth, '/privacy/audit-log/')
  return Array.isArray(res) ? res : res.results ?? []
}

export async function getConsentStatus(
  request: APIRequestContext,
  auth: AuthCookies,
): Promise<any[]> {
  const res = await apiGet<any>(request, auth, '/privacy/consent/')
  return Array.isArray(res) ? res : res.results ?? []
}

export async function getDeletionRequests(
  request: APIRequestContext,
  auth: AuthCookies,
): Promise<any[]> {
  const res = await apiGet<any>(request, auth, '/privacy/delete/requests/')
  return Array.isArray(res) ? res : res.results ?? []
}
