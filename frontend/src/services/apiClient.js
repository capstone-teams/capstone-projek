import { ApiError, mapHttpError, mapRequestError } from './apiError.js';
import { API_BASE_URL, TOKEN_STORAGE_KEY, USE_MOCK } from './config.js';
import { handleMockRequest } from './mock/mockServer.js';
export { ApiError } from './apiError.js';
let memoryToken = null;
let unauthorizedHandler = null;
export function getToken() {
    try { return localStorage.getItem(TOKEN_STORAGE_KEY); }
    catch { return memoryToken; }
}
export function setToken(token) {
    memoryToken = token;
    try {
        if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
        else localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch { /* Session remains available in memory when storage is unavailable. */ }
}
export function onUnauthorized(handler) { unauthorizedHandler = handler; }
export function createApiClient({ baseUrl = '/api/v1', fetchImpl = fetch, } = {}) {
    const base = baseUrl.replace(/\/$/, '');
    const request = async (path, init = {}) => {
        const url = `${base}/${path.replace(/^\//, '')}`;
        const headers = new Headers(init.headers);
        if (!headers.has('Accept'))
            headers.set('Accept', 'application/json');
        try {
            const response = await fetchImpl(url, { ...init, headers });
            const text = await response.text();
            let data;
            if (text) {
                try {
                    data = JSON.parse(text);
                }
                catch {
                    if (!response.ok)
                        throw mapHttpError(response.status, undefined);
                    throw new ApiError('Respons server tidak valid.', 'invalid-response', response.status);
                }
            }
            if (!response.ok)
                throw mapHttpError(response.status, data);
            return data;
        }
        catch (error) {
            throw mapRequestError(error);
        }
    };
    return {
        request,
        get: (path, init) => request(path, { ...init, method: 'GET' }),
        post: (path, body, init = {}) => {
            const headers = new Headers(init.headers);
            const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
            if (body !== undefined && !isFormData && !headers.has('Content-Type')) {
                headers.set('Content-Type', 'application/json');
            }
            return request(path, {
                ...init,
                method: 'POST',
                headers,
                body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
            });
        },
    };
}

// Rakha's service-facing API uses the same validated HTTP engine as FE-03.2.
export async function request(method, path, { body, query, headers = {}, signal } = {}) {
    const token = getToken();
    const unauthorized = () => {
        if (token === getToken()) unauthorizedHandler?.();
    };
    if (signal?.aborted) throw mapRequestError(new DOMException('Aborted', 'AbortError'));
    if (USE_MOCK) {
        const result = await handleMockRequest({ method, path, query, body, token });
        if (signal?.aborted) throw mapRequestError(new DOMException('Aborted', 'AbortError'));
        if (result.status === 401) unauthorized();
        if (result.status >= 400) throw mapHttpError(result.status, result.data);
        return result.data;
    }
    const params = new URLSearchParams(Object.entries(query ?? {}).filter(([, value]) => value != null));
    const suffix = params.size ? `?${params}` : '';
    const client = createApiClient({ baseUrl: API_BASE_URL });
    const init = { signal, headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...headers } };
    try {
        if (method === 'POST') return await client.post(`${path}${suffix}`, body, init);
        if (body !== undefined) {
            const isForm = body instanceof FormData;
            init.body = isForm ? body : JSON.stringify(body);
            if (!isForm) init.headers['Content-Type'] ??= 'application/json';
        }
        return await client.request(`${path}${suffix}`, { ...init, method });
    } catch (error) {
        if (error.status === 401) unauthorized();
        throw error;
    }
}
export const api = {
    get: (path, options) => request('GET', path, options),
    post: (path, body, options) => request('POST', path, { ...options, body }),
    put: (path, body, options) => request('PUT', path, { ...options, body }),
};
export function idempotencyHeader() { return { 'Idempotency-Key': crypto.randomUUID() }; }
export function nullOn404(error) { if (error?.status === 404) return null; throw error; }
