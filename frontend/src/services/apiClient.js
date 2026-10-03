import { API_BASE_URL, TOKEN_STORAGE_KEY, USE_MOCK } from './config';
import { handleMockRequest } from './mock/mockServer';

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
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // localStorage tidak tersedia (mis. private mode); sesi hanya hidup di memori.
  }
}

// Dipanggil saat backend membalas 401 agar AuthContext bisa logout.
let unauthorizedHandler = null;
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

function toApiError(status, payload) {
  const err = payload?.error;
  if (err) return new ApiError(status, err.code, err.message, err.details);
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

  if (USE_MOCK) {
    const res = await handleMockRequest({ method, path, query, body, token });
    if (res.status === 401 && unauthorizedHandler) unauthorizedHandler();
    if (res.status >= 400) throw toApiError(res.status, res.data);
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
      data = null;
    }
  }

  if (response.status === 401 && unauthorizedHandler) unauthorizedHandler();
  if (!response.ok) throw toApiError(response.status, data);
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
