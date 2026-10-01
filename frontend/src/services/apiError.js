export class ApiError extends Error {
  /** @param {string} message @param {string} kind @param {number} [status] @param {string} [code] @param {unknown} [details] */
  constructor(message, kind, status, code, details) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.code = code
    this.details = details
  }
}

/** @param {number} status @param {unknown} body */
export function mapHttpError(status, body) {
  /** @type {{ error?: { code?: unknown, message?: unknown, details?: unknown }, detail?: unknown }} */
  const payload = body && typeof body === 'object' ? body : {}
  const code = typeof payload.error?.code === 'string' ? payload.error.code : undefined
  const apiMessage = typeof payload.error?.message === 'string'
    ? payload.error.message
    : typeof payload.detail === 'string' ? payload.detail : undefined

  const kind = status === 400 || status === 422 ? 'validation'
    : status === 401 ? 'unauthorized'
    : status === 403 ? 'forbidden'
    : status === 404 ? 'not-found'
    : status >= 500 ? 'server'
    : 'unknown'

  const fallbackMessage = {
    validation: 'Permintaan tidak valid.',
    unauthorized: 'Sesi Anda perlu diperbarui.',
    forbidden: 'Anda tidak memiliki akses.',
    'not-found': 'Data tidak ditemukan.',
    server: 'Server sedang mengalami masalah.',
    network: 'Koneksi ke server gagal.',
    cancelled: 'Permintaan dibatalkan.',
    'invalid-response': 'Respons server tidak valid.',
    unknown: 'Permintaan gagal.',
  }

  return new ApiError(apiMessage || fallbackMessage[kind], kind, status, code, payload.error?.details)
}

/** @param {unknown} error */
export function mapRequestError(error) {
  if (error instanceof ApiError) return error
  if (error instanceof Error && error.name === 'AbortError') {
    return new ApiError('Permintaan dibatalkan.', 'cancelled')
  }
  if (error instanceof TypeError) return new ApiError('Koneksi ke server gagal.', 'network')
  return new ApiError('Permintaan gagal.', 'unknown')
}
