import type { ApiResult } from '@/types/api'
import { useAuthStore } from '@/stores/auth-store'

async function request<T>(method: string, url: string, body?: unknown): Promise<ApiResult<T>> {
  try {
    const token = await useAuthStore.getState().getToken()
    const headers: Record<string, string> = {}
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    if (body) {
      headers['Content-Type'] = 'application/json'
    }

    const res = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      return { ok: false, status: res.status, error: data }
    }
    return { ok: true, status: res.status, data: data as T }
  } catch (err) {
    return { ok: false, status: 0, error: err }
  }
}

export const api = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body?: unknown) => request<T>('POST', url, body),
  put: <T>(url: string, body?: unknown) => request<T>('PUT', url, body),
  patch: <T>(url: string, body?: unknown) => request<T>('PATCH', url, body),
  delete: <T>(url: string) => request<T>('DELETE', url),
}
