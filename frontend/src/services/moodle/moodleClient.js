/**
 * Klien Web Service LMS (REST) opsional saat `VITE_MOODLE_URL` dikonfigurasi.
 * Pada mode Single Gateway (produksi), frontend berkomunikasi lewat Backend API (`apiClient.js`).
 */
import { MSG_UNAVAILABLE, logTechnical } from '../../utils/userMessages';

const MOODLE_URL = (import.meta.env.VITE_MOODLE_URL || '').replace(/\/$/, '');
const MOODLE_SERVICE = 'moodle_mobile_app';

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

function requireMoodleUrl() {
  if (!MOODLE_URL) {
    throw new MoodleError('invalidtoken', 'Koneksi langsung Moodle tidak aktif; gunakan Backend Gateway.');
  }
  return MOODLE_URL;
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
  const baseUrl = requireMoodleUrl();
  const data = await postForm(`${baseUrl}/login/token.php`, encodeParams({ username, password, service: MOODLE_SERVICE }));
  if (data.error || !data.token) {
    throw new MoodleError(data.errorcode ?? 'loginfailed', data.error ?? 'Login gagal.');
  }
  return data.token;
}

/** Panggil satu fungsi Web Service LMS, mis. callWs('core_webservice_get_site_info'). */
export async function callWs(wsfunction, params = {}) {
  if (!token) throw new MoodleError('invalidtoken', 'Sesi Moodle belum ada. Silakan login.');
  const baseUrl = requireMoodleUrl();
  const generation = tokenGeneration;

  const data = await postForm(
    `${baseUrl}/webservice/rest/server.php?moodlewsrestformat=json&wsfunction=${encodeURIComponent(wsfunction)}`,
    encodeParams({ wstoken: token, ...params }),
  );

  if (data && typeof data === 'object' && data.exception) {
    if (data.errorcode === 'invalidtoken' && generation === tokenGeneration && onInvalidToken) onInvalidToken();
    throw new MoodleError(data.errorcode, data.message, { exception: data.exception, wsfunction });
  }
  return data;
}

async function uploadToDraft(files, itemid, filepath) {
  const baseUrl = requireMoodleUrl();
  const form = new FormData();
  form.append('token', token);
  form.append('filearea', 'draft');
  form.append('itemid', String(itemid));
  form.append('filepath', filepath);
  files.forEach((file, index) => form.append(`file_${index + 1}`, file, file.name));
  let response;
  try {
    response = await fetch(`${baseUrl}/webservice/upload.php`, { method: 'POST', body: form });
  } catch (cause) {
    logTechnical('lms', { url: `${baseUrl}/webservice/upload.php`, error: String(cause) });
    throw new MoodleError('networkerror', MSG_UNAVAILABLE);
  }
  const data = await response.json().catch(() => null);
  if (!Array.isArray(data) || !data.length) {
    throw new MoodleError(data?.errorcode ?? 'uploadfailed', data?.error ?? 'File gagal diunggah ke Moodle.');
  }
  return data[0].itemid;
}

async function toUploadable(entry) {
  if (entry.file) return entry.file.name === entry.filename ? entry.file : new File([entry.file], entry.filename);
  const response = await fetch(withToken(entry.fileurl)).catch(() => null);
  if (!response?.ok) throw new MoodleError('downloadfailed', `File ${entry.filename} gagal diambil dari Moodle.`);
  return new File([await response.blob()], entry.filename);
}

/** Isi draft area lewat webservice/upload.php dan kembalikan itemid-nya. */
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

/** URL file dari Web Service (webservice/pluginfile.php) butuh token. */
export function withToken(url) {
  if (!url || !token) return url;
  if (!url.includes('/webservice/pluginfile.php') && !url.includes('/pluginfile.php')) return url;
  const fixed = url.replace('/pluginfile.php', url.includes('/webservice/') ? '/pluginfile.php' : '/webservice/pluginfile.php');
  return `${fixed}${fixed.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
}
