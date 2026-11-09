import { API_BASE_URL, TOKEN_STORAGE_KEY } from './config';
import { readString, writeString } from '../utils/storage';
import { MSG_REQUEST_FAILED, MSG_UNAVAILABLE, logTechnical } from '../utils/userMessages';

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

// Pesan cadangan untuk pengguna; kode HTTP dan isi mentah hanya dicatat ke konsol.
const fallbackMessage = (status) => (status >= 500 || status === 0 ? MSG_UNAVAILABLE : MSG_REQUEST_FAILED);

function toApiError(status, payload) {
  if (payload?.error && typeof payload.error === 'object') {
    const err = payload.error;
    return new ApiError(
      status,
      err.code || defaultErrorCode(status),
      err.message || fallbackMessage(status),
      Array.isArray(err.details) ? err.details : (err.details != null ? [err.details] : []),
    );
  }

  // Galat server di luar kontrak backend (mis. halaman galat Cloudflare atau proxy): teksnya teknis dan bukan
  // untuk pengguna, jadi hanya dicatat ke konsol.
  if (status >= 500 || status === 0) {
    logTechnical('api', { status, body: payload });
    return new ApiError(status, status === 0 ? 'NETWORK_ERROR' : 'INTERNAL_ERROR', MSG_UNAVAILABLE);
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
    const message = formatDetail(payload.detail) || fallbackMessage(status);
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

  logTechnical('api', { status, body: payload });
  return new ApiError(status, 'INTERNAL_ERROR', fallbackMessage(status));
}

/**
 * Satu pintu untuk semua request ke Backend API (Single Gateway).
 */
export async function request(method, path, { body, query, headers = {} } = {}) {
  const qs = query
    ? '?' + new URLSearchParams(Object.entries(query).filter(([, v]) => v != null)).toString()
    : '';
  const token = getToken();
  const normalizedPath = path.replace(/\/+$/, '');
  const isAuthLogin = normalizedPath === '/auth/login';

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
  } catch (cause) {
    logTechnical('api', { method, path, error: String(cause) });
    throw networkError();
  }
  return settle(response.status, await response.text(), { token, isAuthLogin });
}

const networkError = () => new ApiError(0, 'NETWORK_ERROR', MSG_UNAVAILABLE);

/** Ubah response HTTP mentah menjadi data, atau lempar ApiError (dipakai fetch dan upload XHR). */
function settle(status, text, { token, isAuthLogin }) {
  const ok = status >= 200 && status < 300;
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      if (ok) {
        logTechnical('api', { status, body: text.slice(0, 200) });
        throw new ApiError(status, 'INVALID_RESPONSE', MSG_UNAVAILABLE);
      }
      data = null;
    }
  }
  if (status === 401 && token && !isAuthLogin && unauthorizedHandler) unauthorizedHandler();
  if (!ok) throw fail(status, data);
  return data;
}

/**
 * Upload multipart dengan laporan progres (fetch tidak melaporkan progres pengiriman).
 * onProgress(persen 0–100).
 */
export function upload(path, form, { onProgress } = {}) {
  const token = getToken();
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE_URL}${path}`);
    xhr.setRequestHeader('Accept', 'application/json');
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => reject(networkError());
    xhr.onload = () => {
      try {
        resolve(settle(xhr.status, xhr.responseText, { token, isAuthLogin: false }));
      } catch (error) {
        reject(error);
      }
    };
    onProgress?.(0);
    xhr.send(form);
  });
}

export const api = {
  get: (path, opts) => request('GET', path, opts),
  post: (path, body, opts) => request('POST', path, { ...opts, body }),
  put: (path, body, opts) => request('PUT', path, { ...opts, body }),
  upload,
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
