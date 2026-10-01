export type ApiErrorKind =
  | 'validation'
  | 'unauthorized'
  | 'forbidden'
  | 'not-found'
  | 'server'
  | 'network'
  | 'cancelled'
  | 'invalid-response'
  | 'unknown'

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status?: number
  readonly code?: string
  readonly details?: unknown

  constructor(
    message: string,
    kind: ApiErrorKind,
    status?: number,
    code?: string,
    details?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.code = code
    this.details = details
  }
}

interface ApiErrorBody {
  error?: {
    code?: unknown
    message?: unknown
    details?: unknown
  }
  detail?: unknown
}

export function mapHttpError(status: number, body: unknown): ApiError {
  const payload = body && typeof body === 'object' ? body as ApiErrorBody : {}
  const code = typeof payload.error?.code === 'string' ? payload.error.code : undefined
  const apiMessage = typeof payload.error?.message === 'string'
    ? payload.error.message
    : typeof payload.detail === 'string' ? payload.detail : undefined

  const kind: ApiErrorKind = status === 400 || status === 422 ? 'validation'
    : status === 401 ? 'unauthorized'
    : status === 403 ? 'forbidden'
    : status === 404 ? 'not-found'
    : status >= 500 ? 'server'
    : 'unknown'

  const fallbackMessage: Record<ApiErrorKind, string> = {
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

export function mapRequestError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (error instanceof Error && error.name === 'AbortError') {
    return new ApiError('Permintaan dibatalkan.', 'cancelled')
  }
  if (error instanceof TypeError) return new ApiError('Koneksi ke server gagal.', 'network')
  return new ApiError('Permintaan gagal.', 'unknown')
}
