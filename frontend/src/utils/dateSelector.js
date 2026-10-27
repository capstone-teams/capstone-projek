// Nilai date_time_selector Moodle: { enabled, date }. Tidak aktif = 0 (tanpa tanggal).

/** Nilai awal date_time_selector: hari ini + `days` pukul 00:00, seperti default mod_form. */
export function dateValue(days, enabled) {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() + days);
  return { enabled, date };
}

export const toUnix = ({ enabled, date }) => (enabled ? Math.floor(date.getTime() / 1000) : 0);
