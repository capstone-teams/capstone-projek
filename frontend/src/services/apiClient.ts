import { ApiError, mapHttpError, mapRequestError } from './apiError.ts'

export interface ApiClient {
  request<T>(path: string, init?: RequestInit): Promise<T>
  get<T>(path: string, init?: RequestInit): Promise<T>
  post<T>(path: string, body?: unknown, init?: RequestInit): Promise<T>
}

export interface ApiClientOptions {
  baseUrl?: string
  fetchImpl?: typeof fetch
}

export function createApiClient({
  baseUrl = '/api/v1',
  fetchImpl = fetch,
}: ApiClientOptions = {}): ApiClient {
  const base = baseUrl.replace(/\/$/, '')

  const request = async <T>(path: string, init: RequestInit = {}): Promise<T> => {
    const url = `${base}/${path.replace(/^\//, '')}`
    const headers = new Headers(init.headers)
    if (!headers.has('Accept')) headers.set('Accept', 'application/json')

    try {
      const response = await fetchImpl(url, { ...init, headers })
      const text = await response.text()
      let data: unknown

      if (text) {
        try {
          data = JSON.parse(text)
        } catch {
          if (!response.ok) throw mapHttpError(response.status, undefined)
          throw new ApiError('Respons server tidak valid.', 'invalid-response', response.status)
        }
      }

      if (!response.ok) throw mapHttpError(response.status, data)
      return data as T
    } catch (error) {
      throw mapRequestError(error)
    }
  }

  return {
    request,
    get: <T>(path: string, init?: RequestInit) => request<T>(path, { ...init, method: 'GET' }),
    post: <T>(path: string, body?: unknown, init: RequestInit = {}) => {
      const headers = new Headers(init.headers)
      const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
      if (body !== undefined && !isFormData && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
      }
      return request<T>(path, {
        ...init,
        method: 'POST',
        headers,
        body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
      })
    },
  }
}
