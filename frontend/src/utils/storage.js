// Akses localStorage yang aman: kegagalan baca/tulis (private mode, kuota penuh,
// data rusak) tidak boleh memutus aplikasi. State tetap hidup di memori.

export function readString(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeString(key, value) {
  try {
    if (value == null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

export function readJson(key, fallback = null) {
  const raw = readString(key);
  if (raw == null) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function writeJson(key, value) {
  return writeString(key, value == null ? null : JSON.stringify(value));
}
