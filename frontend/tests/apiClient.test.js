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

  it('memetakan format error FastAPI detail string ke ApiError', async () => {
    mockFetch(401, { detail: 'Email atau password salah' });
    const err = await request('POST', '/auth/login').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(401);
    expect(err.code).toBe('AUTHENTICATION_FAILED');
    expect(err.message).toBe('Email atau password salah');
    expect(err.details).toEqual(['Email atau password salah']);
  });

  it('memetakan format error FastAPI 422 validation array ke ApiError dengan mapping field dan detail mentah', async () => {
    const rawDetail = [
      { loc: ['body', 'password'], msg: 'Field required', type: 'missing' },
      { loc: ['body', 'profile', 'email'], msg: 'value is not a valid email address', type: 'value_error' },
    ];
    mockFetch(422, { detail: rawDetail });
    const err = await request('POST', '/users').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.code).toBe('VALIDATION_FAILED');
    expect(err.message).toBe('password: Field required, profile.email: value is not a valid email address');
    expect(err.details).toEqual(rawDetail);
  });

  it('menangani format error 422 dengan loc sederhana atau tanpa loc', async () => {
    mockFetch(422, { detail: [{ loc: ['password'], msg: 'Field required' }] });
    const err1 = await request('POST', '/users').catch((e) => e);
    expect(err1.message).toBe('password: Field required');

    mockFetch(422, { detail: [{ msg: 'Invalid payload' }] });
    const err2 = await request('POST', '/users').catch((e) => e);
    expect(err2.message).toBe('Invalid payload');
  });

  it('menangani format error 422 dengan loc bersarang tanpa prefix HTTP scope', async () => {
    mockFetch(422, { detail: [{ loc: ['user', 'profile', 'email'], msg: 'Invalid format' }] });
    const err = await request('POST', '/users').catch((e) => e);
    expect(err.message).toBe('user.profile.email: Invalid format');
  });

  it('menangani format error 422 dengan loc root body dan item tanpa msg', async () => {
    mockFetch(422, { detail: [{ loc: ['body'], msg: 'Field required' }] });
    const err1 = await request('POST', '/users').catch((e) => e);
    expect(err1.message).toBe('body: Field required');

    mockFetch(422, { detail: [{ loc: ['body', 'password'], type: 'missing' }] });
    const err2 = await request('POST', '/users').catch((e) => e);
    expect(err2.message).toBe('password: missing');
  });

  it('memetakan format error payload dengan error string atau pesan generik ke ApiError', async () => {
    mockFetch(400, { error: 'invalid_grant', error_description: 'Bad credentials' });
    const err1 = await request('POST', '/token').catch((e) => e);
    expect(err1.status).toBe(400);
    expect(err1.code).toBe('INVALID_REQUEST');
    expect(err1.message).toBe('Bad credentials');

    mockFetch(404, { message: 'Entity tidak ditemukan.' });
    const err2 = await request('GET', '/items/99').catch((e) => e);
    expect(err2.status).toBe(404);
    expect(err2.code).toBe('RESOURCE_NOT_FOUND');
    expect(err2.message).toBe('Entity tidak ditemukan.');
  });

  it('memetakan format error detail objek dengan kode kustom ke ApiError', async () => {
    mockFetch(400, { detail: { code: 'INVALID_STATE', message: 'Tidak dapat diproses' } });
    const err = await request('POST', '/action').catch((e) => e);
    expect(err.status).toBe(400);
    expect(err.code).toBe('INVALID_STATE');
    expect(err.message).toBe('Tidak dapat diproses');
  });

  it('menggunakan fallback pesan dan INTERNAL_ERROR bila payload error kosong', async () => {
    mockFetch(500, null);
    const err = await request('GET', '/broken').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(500);
    expect(err.code).toBe('INTERNAL_ERROR');
    expect(err.message).toBe('Request gagal (HTTP 500).');
  });

  it('menyisipkan Authorization Bearer token bila token tersedia di storage', async () => {
    setToken('token-storage-xyz');
    const fetchFn = mockFetch(200, { ok: true });
    await request('GET', '/courses');
    const [, init] = fetchFn.mock.calls[0];
    expect(init.headers.Authorization).toBe('Bearer token-storage-xyz');
  });

  it('tidak menyisipkan Authorization header bila token bernilai null', async () => {
    setToken(null);
    const fetchFn = mockFetch(200, { ok: true });
    await request('GET', '/courses');
    const [, init] = fetchFn.mock.calls[0];
    expect(init.headers.Authorization).toBeUndefined();
  });

  it('memanggil handler unauthorized saat token ditolak (401)', async () => {
    const handler = vi.fn();
    onUnauthorized(handler);
    setToken('expired');
    mockFetch(401, { error: { code: 'AUTHENTICATION_FAILED', message: 'x' } });
    await request('GET', '/auth/me').catch(() => {});
    expect(handler).toHaveBeenCalledOnce();
  });

  it('401 tanpa token (password salah saat login) tidak dianggap sesi berakhir', async () => {
    const handler = vi.fn();
    onUnauthorized(handler);
    mockFetch(401, { error: { code: 'AUTHENTICATION_FAILED', message: 'Autentikasi gagal.' } });
    await expect(login('dosen', 'salah')).rejects.toMatchObject({ code: 'AUTHENTICATION_FAILED', message: 'Autentikasi gagal.' });
    expect(handler).not.toHaveBeenCalled();
    expect(getToken()).toBeNull();
  });

  it('memanggil handler unauthorized saat 401 dengan format FastAPI detail', async () => {
    const handler = vi.fn();
    onUnauthorized(handler);
    setToken('expired');
    mockFetch(401, { detail: 'Token expired' });
    const err = await request('GET', '/auth/me').catch((e) => e);
    expect(handler).toHaveBeenCalledOnce();
    expect(err.status).toBe(401);
    expect(err.code).toBe('AUTHENTICATION_FAILED');
    expect(err.message).toBe('Token expired');
  });

  it('tidak memanggil handler unauthorized saat 401 terjadi pada endpoint login (/auth/login)', async () => {
    const handler = vi.fn();
    onUnauthorized(handler);
    // Token lama tetap tersimpan: aturan path saja yang mencegah logout paksa.
    setToken('stale');
    mockFetch(401, { detail: 'Email atau password salah' });
    const err = await request('POST', '/auth/login', { body: { username: 'dosen', password: 'wrong' } }).catch((e) => e);
    expect(handler).not.toHaveBeenCalled();
    expect(err.status).toBe(401);
    expect(err.code).toBe('AUTHENTICATION_FAILED');
    expect(err.message).toBe('Email atau password salah');
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
