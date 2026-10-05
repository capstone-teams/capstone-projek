import { afterEach, describe, expect, it, vi } from 'vitest';

// Uji jalur HTTP sungguhan (bukan mock) dengan fetch tiruan.
vi.mock('../src/services/config', () => ({
  API_BASE_URL: '/api/v1',
  USE_MOCK: false,
  MOODLE_URL: 'http://moodle.test',
  TOKEN_STORAGE_KEY: 'test.token',
}));

const { request, getToken, setToken, ApiError, onUnauthorized } = await import('../src/services/apiClient');
const { login } = await import('../src/services/authService');

function mockFetch(status, body) {
  const fn = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(body === undefined ? '' : JSON.stringify(body)),
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setToken(null);
  onUnauthorized(null);
});

describe('apiClient (mode backend)', () => {
  it('mengirim JSON + bearer token ke base URL', async () => {
    setToken('abc');
    const fetchFn = mockFetch(200, { ok: true });
    const data = await request('POST', '/courses', { body: { rps_id: 'rps_001' }, query: { week: 2, skip: null } });

    expect(data).toEqual({ ok: true });
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe('/api/v1/courses?week=2');
    expect(init.method).toBe('POST');
    expect(init.headers.Authorization).toBe('Bearer abc');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body)).toEqual({ rps_id: 'rps_001' });
  });

  it('tidak memaksa Content-Type untuk FormData', async () => {
    const fetchFn = mockFetch(201, { id: 'rps_1' });
    const form = new FormData();
    form.append('file', new Blob(['x']), 'a.pdf');
    await request('POST', '/rps', { body: form });
    const [, init] = fetchFn.mock.calls[0];
    expect(init.headers['Content-Type']).toBeUndefined();
    expect(init.body).toBe(form);
  });

  it('memetakan format error backend ke ApiError', async () => {
    mockFetch(422, { error: { code: 'VALIDATION_FAILED', message: 'Gagal', details: ['x'] } });
    const err = await request('GET', '/x').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 422, code: 'VALIDATION_FAILED', message: 'Gagal', details: ['x'] });
  });

  it('memanggil handler unauthorized saat 401', async () => {
    const handler = vi.fn();
    onUnauthorized(handler);
    mockFetch(401, { error: { code: 'AUTHENTICATION_FAILED', message: 'x' } });
    await request('GET', '/auth/me').catch(() => {});
    expect(handler).toHaveBeenCalledOnce();
  });

  it('melaporkan NETWORK_ERROR bila backend mati', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const err = await request('GET', '/x').catch((e) => e);
    expect(err.code).toBe('NETWORK_ERROR');
  });

  it('rejects malformed successful JSON instead of presenting it as empty data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, text: async () => '<html>Proxy error</html>' }));
    await expect(request('GET', '/courses')).rejects.toMatchObject({ code: 'INVALID_RESPONSE', status: 200 });
  });

  it('accepts a valid empty 204 response', async () => {
    mockFetch(204);
    await expect(request('POST', '/x')).resolves.toBeNull();
  });

  it('a delayed backend login cannot restore a token after its session ended', async () => {
    let release;
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise((resolve) => { release = resolve; })));
    let current = true;
    const pending = login('dosen', 'dosen123', { isCurrent: () => current });
    current = false;
    release({ ok: true, status: 200, text: async () => JSON.stringify({ access_token: 'obsolete-token' }) });
    await pending;
    expect(getToken()).toBeNull();
  });
});
