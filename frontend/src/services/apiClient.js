import { ApiError, mapHttpError, mapRequestError } from './apiError.js'

/** @param {{ baseUrl?: string, fetchImpl?: typeof fetch }} options */
export function createApiClient({
  baseUrl = '/api/v1',
  fetchImpl = fetch,
} = {}) {
  const base = baseUrl.replace(/\/$/, '')

  /** @param {string} path @param {RequestInit} init */
  const request = async (path, init = {}) => {
    const url = `${base}/${path.replace(/^\//, '')}`
    const headers = new Headers(init.headers)
    if (!headers.has('Accept')) headers.set('Accept', 'application/json')

    try {
      const response = await fetchImpl(url, { ...init, headers })
      const text = await response.text()
      let data

      if (text) {
        try {
          data = JSON.parse(text)
        } catch {
          if (!response.ok) throw mapHttpError(response.status, undefined)
          throw new ApiError('Respons server tidak valid.', 'invalid-response', response.status)
        }
      }

      if (!response.ok) throw mapHttpError(response.status, data)
      return data
    } catch (error) {
      throw mapRequestError(error)
    }
  }

  return {
    request,
    /** @param {string} path @param {RequestInit} [init] */
    get: (path, init) => request(path, { ...init, method: 'GET' }),
    /** @param {string} path @param {unknown} [body] @param {RequestInit} [init] */
    post: (path, body, init = {}) => {
      const headers = new Headers(init.headers)
      const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
      if (body !== undefined && !isFormData && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
      }
      return request(path, {
        ...init,
        method: 'POST',
        headers,
        body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
      })
    },
  }
}
