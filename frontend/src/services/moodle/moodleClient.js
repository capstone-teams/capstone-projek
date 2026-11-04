/**
<<<<<<< HEAD
 * Klien Moodle Web Service (REST).
=======
 * Klien Web Service LMS (REST).
 *
 * STATUS: sementara, karena API backend belum menyediakan data ini. Frontend seharusnya hanya
 * memanggil backend (design-api §25). Saat ini VITE_MOODLE_MOCK=true, jadi semua panggilan dijawab
 * mockMoodle.js dan tidak ada request ke server LMS.
 *
 * Rujukan dokumentasi Moodle:
 *  - Token   : POST {MOODLE_URL}/login/token.php
 *  - Fungsi  : POST {MOODLE_URL}/webservice/rest/server.php
 *  - Daftar fungsi dan parameter: lib/db/services.php dan db/services.php tiap plugin, atau
 *    Site administration > Server > Web services > API Documentation.
 *
 * Kedua endpoint mengirim header Access-Control-Allow-Origin: *, jadi bisa dipanggil dari browser.
>>>>>>> develop
 */
import { MOODLE_SERVICE, MOODLE_URL, USE_MOCK, USE_MOODLE_MOCK } from '../config';
import { mockCallWs, mockRequestToken, mockUploadDraftFiles } from '../mock/mockMoodle';
import { MSG_UNAVAILABLE, logTechnical } from '../../utils/userMessages';

export class MoodleError extends Error {
  constructor(errorcode, message, extra = {}) {
    super(message);
    this.name = 'MoodleError';
    this.code = errorcode;
    Object.assign(this, extra);
  }
}

let token = null;
let tokenGeneration = 0;
let onInvalidToken = null;

export function setMoodleToken(value) {
  token = value;
  tokenGeneration += 1;
}

/** Dipanggil saat token LMS ditolak (mis. kedaluwarsa atau dicabut). */
export function onMoodleTokenInvalid(handler) {
  onInvalidToken = handler;
}

/**
 * Ubah objek bersarang ke format form yang diminta Web Service LMS:
 * { courseids: [2, 3] } -> courseids[0]=2&courseids[1]=3
 * { options: [{ name: 'x', value: 1 }] } -> options[0][name]=x&options[0][value]=1
 */
export function encodeParams(params, prefix = '', out = new URLSearchParams()) {
  Object.entries(params ?? {}).forEach(([key, value]) => {
    const name = prefix ? `${prefix}[${key}]` : key;
    if (value === undefined || value === null) return;
    if (typeof value === 'object') encodeParams(value, name, out);
    else if (typeof value === 'boolean') out.append(name, value ? '1' : '0');
    else out.append(name, String(value));
  });
  return out;
}

async function postForm(url, body) {
  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
  } catch (cause) {
    logTechnical('lms', { url, error: String(cause) });
    throw new MoodleError('networkerror', MSG_UNAVAILABLE);
  }
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    logTechnical('lms', { url, status: response.status, body: text.slice(0, 200) });
    throw new MoodleError('invalidresponse', MSG_UNAVAILABLE);
  }
}

/** Login ke LMS dan dapatkan token layanan. */
export async function requestToken(username, password) {
  // Backend nyata sudah memverifikasi kata sandi; fixture mock tidak memegang kata sandi akun itu.
  if (USE_MOODLE_MOCK) return mockRequestToken(username, password, { trusted: !USE_MOCK });

  const data = await postForm(`${MOODLE_URL}/login/token.php`, encodeParams({ username, password, service: MOODLE_SERVICE }));
  if (data.error || !data.token) {
    throw new MoodleError(data.errorcode ?? 'loginfailed', data.error ?? 'Login gagal.');
  }
  return data.token;
}

/** Panggil satu fungsi Web Service LMS, mis. callWs('core_webservice_get_site_info'). */
export async function callWs(wsfunction, params = {}) {
  const requestToken = token || (USE_MOODLE_MOCK ? 'mock-3-session' : null);
  if (!requestToken) throw new MoodleError('invalidtoken', 'Sesi Moodle belum ada. Silakan login.');
  const generation = tokenGeneration;

  const data = USE_MOODLE_MOCK
    ? await mockCallWs(requestToken, wsfunction, params)
    : await postForm(
        `${MOODLE_URL}/webservice/rest/server.php?moodlewsrestformat=json&wsfunction=${encodeURIComponent(wsfunction)}`,
        encodeParams({ wstoken: requestToken, ...params }),
      );

  if (data && typeof data === 'object' && data.exception) {
    if (data.errorcode === 'invalidtoken' && generation === tokenGeneration && onInvalidToken) onInvalidToken();
    throw new MoodleError(data.errorcode, data.message, { exception: data.exception, wsfunction });
  }
  return data;
}

/**
 * Unggah file ke draft area pengguna lewat webservice/upload.php. Rujukan: dipakai juga aplikasi Moodle mobile.
 * Mengembalikan itemid draft untuk parameter *_filemanager, mis. files_filemanager pada pengumpulan tugas.
 */
async function uploadToDraft(files, itemid, filepath) {
  let data;
  const activeToken = token || (USE_MOODLE_MOCK ? 'mock-3-session' : null);
  if (USE_MOODLE_MOCK) {
    data = await mockUploadDraftFiles(activeToken, files, { itemid, filepath });
  } else {
    const form = new FormData();
    form.append('token', activeToken);
    form.append('filearea', 'draft');
    form.append('itemid', String(itemid));
    form.append('filepath', filepath);
    files.forEach((file, index) => form.append(`file_${index + 1}`, file, file.name));
    let response;
    try {
      response = await fetch(`${MOODLE_URL}/webservice/upload.php`, { method: 'POST', body: form });
    } catch (cause) {
      logTechnical('lms', { url: `${MOODLE_URL}/webservice/upload.php`, error: String(cause) });
      throw new MoodleError('networkerror', MSG_UNAVAILABLE);
    }
    data = await response.json().catch(() => null);
  }
  if (!Array.isArray(data) || !data.length) {
    throw new MoodleError(data?.errorcode ?? 'uploadfailed', data?.error ?? 'File gagal diunggah ke Moodle.');
  }
  return data[0].itemid;
}

// File yang sudah tersimpan diunduh lagi agar ikut ke draft baru. Rujukan: cara kerja aplikasi Moodle mobile.
// Nama mengikuti entri (bisa sudah diganti, mis. "laporan (1).pdf"), bukan nama file aslinya.
async function toUploadable(entry) {
  if (USE_MOODLE_MOCK) return { name: entry.filename, size: entry.file?.size ?? entry.filesize };
  if (entry.file) return entry.file.name === entry.filename ? entry.file : new File([entry.file], entry.filename);
  const response = await fetch(withToken(entry.fileurl)).catch(() => null);
  if (!response?.ok) throw new MoodleError('downloadfailed', `File ${entry.filename} gagal diambil dari Moodle.`);
  return new File([await response.blob()], entry.filename);
}

/**
 * Isi draft area lewat webservice/upload.php dan kembalikan itemid-nya.
 * entries: [{ filepath, filename, file?: File, filesize?, fileurl? }]; tanpa `file`, file lama diunduh ulang.
 * Tanpa entri, draft kosong dari core_files_get_unused_draft_itemid dipakai untuk mengosongkan area file.
 */
export async function uploadDraftFiles(entries) {
  const requestToken = token || (USE_MOODLE_MOCK ? 'mock-3-session' : null);
  if (!requestToken) throw new MoodleError('invalidtoken', 'Sesi Moodle belum ada. Silakan login.');
  if (!entries.length) return (await callWs('core_files_get_unused_draft_itemid', {})).itemid;
  const byPath = new Map();
  entries.forEach((entry) => byPath.set(entry.filepath ?? '/', [...(byPath.get(entry.filepath ?? '/') ?? []), entry]));
  let itemid = 0;
  for (const [filepath, group] of byPath) {
    itemid = await uploadToDraft(await Promise.all(group.map(toUploadable)), itemid, filepath);
  }
  return itemid;
}

/**
<<<<<<< HEAD
 * Menyisipkan token akses pada URL file Moodle jika diperlukan.
=======
 * URL file dari Web Service (webservice/pluginfile.php) butuh token.
 * Rujukan source Moodle: public/webservice/pluginfile.php.
>>>>>>> develop
 */
export function withToken(url) {
  if (!url || !token || USE_MOODLE_MOCK) return url;
  if (!url.includes('/webservice/pluginfile.php') && !url.includes('/pluginfile.php')) return url;
  const fixed = url.replace('/pluginfile.php', url.includes('/webservice/') ? '/pluginfile.php' : '/webservice/pluginfile.php');
  return `${fixed}${fixed.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
}
<<<<<<< HEAD

/** URL absolut di Moodle. */
export function moodleUrl(path) {
  if (!path) return MOODLE_URL;
  return /^https?:/.test(path) ? path : `${MOODLE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
}
=======
>>>>>>> develop
