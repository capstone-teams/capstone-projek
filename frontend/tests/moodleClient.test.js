import { afterEach, describe, expect, it, vi } from 'vitest';

// Uji jalur Moodle sungguhan (bukan mock) dengan fetch tiruan.
vi.mock('../src/services/config', () => ({
  MOODLE_URL: 'http://moodle.test',
  MOODLE_SERVICE: 'moodle_mobile_app',
  USE_MOODLE_MOCK: false,
}));

const { callWs, encodeParams, MoodleError, onMoodleTokenInvalid, requestToken, setMoodleToken, withToken } = await import(
  '../src/services/moodle/moodleClient'
);
const { resolveSession } = await import('../src/services/moodle/moodleApi');

function mockFetch(...responses) {
  const fn = vi.fn();
  responses.forEach((body) => fn.mockResolvedValueOnce({ status: 200, text: () => Promise.resolve(JSON.stringify(body)) }));
  vi.stubGlobal('fetch', fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setMoodleToken(null);
});

describe('encodeParams', () => {
  it('mengikuti format array/objek Moodle', () => {
    const qs = encodeParams({ courseids: [2, 3], options: [{ name: 'x', value: true }], skip: null }).toString();
    expect(decodeURIComponent(qs)).toBe('courseids[0]=2&courseids[1]=3&options[0][name]=x&options[0][value]=1');
  });
});

describe('login/token.php', () => {
  it('mengirim username, password, dan service', async () => {
    const fetchFn = mockFetch({ token: 'abc', privatetoken: null });
    expect(await requestToken('dosen', 'dosen123')).toBe('abc');
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe('http://moodle.test/login/token.php');
    expect(init.body.toString()).toBe('username=dosen&password=dosen123&service=moodle_mobile_app');
  });

  it('memetakan error login Moodle', async () => {
    mockFetch({ error: 'Invalid login, please try again', errorcode: 'invalidlogin' });
    const err = await requestToken('x', 'y').catch((e) => e);
    expect(err).toBeInstanceOf(MoodleError);
    expect(err.code).toBe('invalidlogin');
  });
});

describe('webservice/rest/server.php', () => {
  it('memanggil fungsi dengan wstoken dan format json', async () => {
    setMoodleToken('tok');
    const fetchFn = mockFetch({ sitename: 'Moodle' });
    await callWs('core_course_get_contents', { courseid: 2 });
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe('http://moodle.test/webservice/rest/server.php?moodlewsrestformat=json&wsfunction=core_course_get_contents');
    expect(init.body.toString()).toBe('wstoken=tok&courseid=2');
  });

  it('melempar MoodleError dan memanggil handler token tidak valid', async () => {
    setMoodleToken('tok');
    const handler = vi.fn();
    onMoodleTokenInvalid(handler);
    mockFetch({ exception: 'moodle_exception', errorcode: 'invalidtoken', message: 'Invalid token' });
    const err = await callWs('core_webservice_get_site_info').catch((e) => e);
    expect(err.code).toBe('invalidtoken');
    expect(handler).toHaveBeenCalledOnce();
  });

  it('melaporkan Moodle mati sebagai networkerror', async () => {
    setMoodleToken('tok');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const err = await callWs('core_webservice_get_site_info').catch((e) => e);
    expect(err.code).toBe('networkerror');
  });
});

describe('resolveSession', () => {
  const site = { sitename: 'Moodle ITK', siteurl: 'http://moodle.test', userid: 3, username: 'dosen', fullname: 'Rina Kartika', firstname: 'Rina', userissiteadmin: false };
  const courses = [{ id: 2 }, { id: 3 }];

  it('dosen bila punya opsi administrasi course', async () => {
    setMoodleToken('tok');
    mockFetch(site, courses, {
      courses: [
        { id: 2, options: [{ name: 'update', available: true }] },
        { id: 3, options: [{ name: 'update', available: false }, { name: 'badges', available: true }] },
      ],
    });
    const { user } = await resolveSession();
    expect(user.role).toBe('dosen');
    expect(user.teacherCourseIds).toEqual([2]);
  });

  it('mahasiswa bila tidak punya opsi administrasi', async () => {
    setMoodleToken('tok');
    mockFetch(site, courses, { courses: courses.map((c) => ({ id: c.id, options: [{ name: 'badges', available: true }] })) });
    const { user } = await resolveSession();
    expect(user.role).toBe('mahasiswa');
  });
});

describe('withToken', () => {
  it('menambahkan token ke URL pluginfile', () => {
    setMoodleToken('tok');
    expect(withToken('http://moodle.test/pluginfile.php/1/mod_page/content/a.png')).toBe(
      'http://moodle.test/webservice/pluginfile.php/1/mod_page/content/a.png?token=tok',
    );
    expect(withToken('http://moodle.test/webservice/pluginfile.php/1/x.pdf?forcedownload=1')).toBe(
      'http://moodle.test/webservice/pluginfile.php/1/x.pdf?forcedownload=1&token=tok',
    );
    expect(withToken('https://developer.mozilla.org')).toBe('https://developer.mozilla.org');
  });
});
