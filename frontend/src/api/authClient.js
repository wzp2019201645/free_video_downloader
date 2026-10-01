import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  withCredentials: true,
})

export function errorText(err, fallback) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  return fallback
}

export async function fetchMe() {
  const { data } = await api.get('/auth/me')
  return data.user
}

export async function registerAccount(email, password) {
  const { data } = await api.post('/auth/register', { email, password })
  return data.user
}

export async function loginAccount(email, password) {
  const { data } = await api.post('/auth/login', { email, password })
  return data.user
}

export async function logoutAccount() {
  await api.post('/auth/logout')
}

export async function fetchPlan() {
  const { data } = await api.get('/billing/plan')
  return data
}

export async function startCheckout() {
  const { data } = await api.post('/billing/checkout')
  return data.url
}

export async function startPortal() {
  const { data } = await api.post('/billing/portal')
  return data.url
}

export async function confirmCheckout(sessionId) {
  const { data } = await api.post('/billing/confirm', { session_id: sessionId })
  return data.user
}
