import { API_BASE_URL, TOKEN_STORAGE_KEY, USE_MOCK } from './config';
import { handleMockRequest } from './mock/mockServer';
import { readString, writeString } from '../utils/storage';

/**
 * Error dari Backend API. Bentuknya mengikuti design-api.md §18:
 * { "error": { "code": "...", "message": "...", "details": [] } }
 */
export class ApiError extends Error {
  constructor(status, code, message, details = []) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function getToken() {
  return readString(TOKEN_STORAGE_KEY);
}

export function setToken(token) {
  writeString(TOKEN_STORAGE_KEY, token || null);
}

// Dipanggil saat backend menolak token (401) agar AuthContext bisa logout.
// 401 tanpa token (mis. password salah saat login) bukan sesi yang berakhir.
let unauthorizedHandler = null;
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

// Dipanggil saat backend menolak role user (403 AUTHORIZATION_DENIED) agar layout menampilkan halaman 403.
let forbiddenHandler = null;
export function onForbidden(handler) {
  forbiddenHandler = handler;
}

function fail(status, payload) {
  const error = toApiError(status, payload);
  if (error.code === 'AUTHORIZATION_DENIED' && forbiddenHandler) forbiddenHandler(error);
  return error;
}

const REQUEST_LOC_PREFIXES = new Set(['body', 'query', 'path', 'header', 'cookie']);

function formatValidationItem(item) {
  if (typeof item === 'string') return item;
  if (!item || typeof item !== 'object') return String(item ?? '');

  const loc = item.loc;
  let field = '';
  if (Array.isArray(loc) && loc.length > 0) {
    const parts = REQUEST_LOC_PREFIXES.has(loc[0]) && loc.length > 1 ? loc.slice(1) : loc;
    field = parts.map((p) => String(p ?? '')).filter(Boolean).join('.');
  } else if (typeof loc === 'string') {
    field = loc;
  }

  const rawMsg = item.msg ?? item.message;
  let msg = '';
  if (typeof rawMsg === 'string' && rawMsg.length > 0) {
    msg = rawMsg;
  } else if (rawMsg != null && rawMsg !== '') {
    msg = String(rawMsg);
  } else if (item.type) {
    msg = String(item.type);
  } else {
    msg = 'Invalid value';
  }

  return field ? `${field}: ${msg}` : msg;
}

function formatDetail(detail) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(formatValidationItem).filter(Boolean).join(', ');
  }
  if (detail && typeof detail === 'object') {
    return detail.message || detail.msg || (detail.detail ? formatDetail(detail.detail) : JSON.stringify(detail));
  }
  if (detail != null) {
    return String(detail);
  }
  return '';
}

function defaultErrorCode(status) {
  if (status === 401) return 'AUTHENTICATION_FAILED';
  if (status === 403) return 'AUTHORIZATION_DENIED';
  if (status === 404) return 'RESOURCE_NOT_FOUND';
  if (status === 409) return 'INVALID_REQUEST';
  if (status === 422) return 'VALIDATION_FAILED';
  if (status === 400) return 'INVALID_REQUEST';
  return 'API_ERROR';
}

export function toApiError(status, payload) {
  if (payload?.error && typeof payload.error === 'object') {
    const err = payload.error;
    return new ApiError(
      status,
      err.code || defaultErrorCode(status),
      err.message || `Request gagal (HTTP ${status}).`,
      Array.isArray(err.details) ? err.details : (err.details != null ? [err.details] : []),
    );
  }

  if (typeof payload?.error === 'string') {
    return new ApiError(
      status,
      defaultErrorCode(status),
      payload.error_description || payload.error,
      [payload.error],
    );
  }

  if (payload?.detail !== undefined && payload?.detail !== null) {
    const code = (typeof payload.detail === 'object' && !Array.isArray(payload.detail) && (payload.detail.code || payload.detail.error_code))
      || defaultErrorCode(status);
    const message = formatDetail(payload.detail) || `Request gagal (HTTP ${status}).`;
    const details = Array.isArray(payload.detail) ? payload.detail : [payload.detail];
    return new ApiError(status, code, message, details);
  }

  if (typeof payload?.message === 'string' && payload.message) {
    return new ApiError(
      status,
      defaultErrorCode(status),
      payload.message,
      [],
    );
  }

  return new ApiError(status, 'INTERNAL_ERROR', `Request gagal (HTTP ${status}).`);
}

/**
 * Satu pintu untuk semua request ke Backend API.
 * Saat USE_MOCK aktif, request dijawab oleh mockServer dengan kontrak yang sama.
 */
export async function request(method, path, { body, query, headers = {} } = {}) {
  const qs = query
    ? '?' + new URLSearchParams(Object.entries(query).filter(([, v]) => v != null)).toString()
    : '';
  const token = getToken();
  const normalizedPath = path.replace(/\/+$/, '');
  const isAuthLogin = normalizedPath === '/auth/login';

  if (USE_MOCK) {
    const res = await handleMockRequest({ method, path, query, body, token });
    if (res.status === 401 && token && !isAuthLogin && unauthorizedHandler) unauthorizedHandler();
    if (res.status >= 400) throw fail(res.status, res.data);
    return res.data;
  }

  const isForm = body instanceof FormData;
  const init = {
    method,
    headers: {
      Accept: 'application/json',
      ...(isForm || body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  };

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}${qs}`, init);
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Tidak dapat terhubung ke server backend.');
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      if (response.ok) throw new ApiError(response.status, 'INVALID_RESPONSE', 'Respons JSON backend tidak valid.');
      data = null;
    }
  }

  if (response.status === 401 && token && !isAuthLogin && unauthorizedHandler) unauthorizedHandler();
  if (!response.ok) throw fail(response.status, data);
  return data;
}

export const api = {
  get: (path, opts) => request('GET', path, opts),
  post: (path, body, opts) => request('POST', path, { ...opts, body }),
  put: (path, body, opts) => request('PUT', path, { ...opts, body }),
};

// Header untuk operasi yang idempoten (design-api.md §21).
export function idempotencyHeader() {
  const key = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return { 'Idempotency-Key': key };
}

// Untuk resource opsional: 404 berarti "belum ada", bukan error.
export function nullOn404(error) {
  if (error?.status === 404) return null;
  throw error;
}
