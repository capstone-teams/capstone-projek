/**
 * Klien Moodle Web Service (REST).
 *
 * Mengikuti dokumentasi Moodle:
 *  - Token   : POST {MOODLE_URL}/login/token.php            (moodle/public/login/token.php)
 *  - Fungsi  : POST {MOODLE_URL}/webservice/rest/server.php (moodle/public/webservice/rest/server.php)
 *  - Daftar fungsi & parameter: moodle/public/lib/db/services.php dan db/services.php tiap plugin,
 *    atau Site administration > Server > Web services > API Documentation di instance Moodle.
 *
 * Kedua endpoint mengirim header Access-Control-Allow-Origin: *, jadi bisa dipanggil dari browser.
 */
import { MOODLE_SERVICE, MOODLE_URL, USE_MOODLE_MOCK } from '../config';
import { mockCallWs, mockRequestToken, mockUploadDraftFiles } from '../mock/mockMoodle';

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

/** Dipanggil saat Moodle menolak token (mis. kedaluwarsa atau dicabut). */
export function onMoodleTokenInvalid(handler) {
  onInvalidToken = handler;
}

/**
 * Ubah objek bersarang ke format form Moodle:
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
  } catch {
    throw new MoodleError('networkerror', `Tidak dapat terhubung ke Moodle di ${MOODLE_URL}. Pastikan Moodle sudah berjalan.`);
  }
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new MoodleError('invalidresponse', `Respons Moodle tidak valid (HTTP ${response.status}).`);
  }
}

/** Login dengan username/password Moodle dan dapatkan token layanan mobile. */
export async function requestToken(username, password) {
  if (USE_MOODLE_MOCK) return mockRequestToken(username, password);

  const data = await postForm(`${MOODLE_URL}/login/token.php`, encodeParams({ username, password, service: MOODLE_SERVICE }));
  if (data.error || !data.token) {
    throw new MoodleError(data.errorcode ?? 'loginfailed', data.error ?? 'Login gagal.');
  }
  return data.token;
}

/** Panggil satu fungsi Moodle Web Service, mis. callWs('core_webservice_get_site_info'). */
export async function callWs(wsfunction, params = {}) {
  if (!token) throw new MoodleError('invalidtoken', 'Sesi Moodle belum ada. Silakan login.');
  const requestToken = token;
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
 * Unggah file ke draft area pengguna lewat webservice/upload.php (dipakai juga aplikasi Moodle mobile).
 * Mengembalikan itemid draft untuk parameter *_filemanager, mis. files_filemanager pada pengumpulan tugas.
 */
async function uploadToDraft(files, itemid, filepath) {
  let data;
  if (USE_MOODLE_MOCK) {
    data = await mockUploadDraftFiles(token, files, { itemid, filepath });
  } else {
    const form = new FormData();
    form.append('token', token);
    form.append('filearea', 'draft');
    form.append('itemid', String(itemid));
    form.append('filepath', filepath);
    files.forEach((file, index) => form.append(`file_${index + 1}`, file, file.name));
    let response;
    try {
      response = await fetch(`${MOODLE_URL}/webservice/upload.php`, { method: 'POST', body: form });
    } catch {
      throw new MoodleError('networkerror', `Tidak dapat terhubung ke Moodle di ${MOODLE_URL}. Pastikan Moodle sudah berjalan.`);
    }
    data = await response.json().catch(() => null);
  }
  if (!Array.isArray(data) || !data.length) {
    throw new MoodleError(data?.errorcode ?? 'uploadfailed', data?.error ?? 'File gagal diunggah ke Moodle.');
  }
  return data[0].itemid;
}

// File yang sudah ada di Moodle diunduh lagi agar ikut ke draft baru (seperti aplikasi Moodle).
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
  if (!token) throw new MoodleError('invalidtoken', 'Sesi Moodle belum ada. Silakan login.');
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
 * URL file Moodle dari Web Service (webservice/pluginfile.php) butuh token.
 * Lihat moodle/public/webservice/pluginfile.php.
 */
export function withToken(url) {
  if (!url || !token || USE_MOODLE_MOCK) return url;
  if (!url.includes('/webservice/pluginfile.php') && !url.includes('/pluginfile.php')) return url;
  const fixed = url.replace('/pluginfile.php', url.includes('/webservice/') ? '/pluginfile.php' : '/webservice/pluginfile.php');
  return `${fixed}${fixed.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
}

/** URL absolut di Moodle (dipakai untuk URL file/tautan konten; bukan untuk mengarahkan pengguna ke Moodle). */
export function moodleUrl(path) {
  if (!path) return MOODLE_URL;
  return /^https?:/.test(path) ? path : `${MOODLE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
}
