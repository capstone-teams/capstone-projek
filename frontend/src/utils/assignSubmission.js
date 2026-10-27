// Jenis pengumpulan tugas Moodle (Assignment > Submission types) dari `configs` mod_assign_get_assignments.
import { formatFileSize } from './format';

const MB = 1024 * 1024;
// Batas ukuran ditulis seperti display_size() Moodle: "1 MB", bukan "1.0 MB".
export const formatLimit = (bytes) => (bytes >= MB ? `${Number((bytes / MB).toFixed(1))} MB` : formatFileSize(bytes));

const configValue = (assign, plugin, name) =>
  Number(assign.configs?.find((c) => c.subtype === 'assignsubmission' && c.plugin === plugin && c.name === name)?.value ?? 0);

export function submissionTypes(assign) {
  const wordlimitEnabled = configValue(assign, 'onlinetext', 'wordlimitenabled') === 1;
  return {
    onlineText: configValue(assign, 'onlinetext', 'enabled') === 1,
    wordLimit: wordlimitEnabled ? configValue(assign, 'onlinetext', 'wordlimit') : 0,
    files: configValue(assign, 'file', 'enabled') === 1,
    maxFiles: configValue(assign, 'file', 'maxfilesubmissions') || 1,
    maxBytes: configValue(assign, 'file', 'maxsubmissionsizebytes'),
  };
}

/** Hitungan kata seperti Moodle: tag diabaikan, singkatan seperti "I'm" dihitung satu kata. */
export function countWords(text) {
  return text.replace(/<[^>]*>/g, ' ').trim().split(/\s+/).filter(Boolean).length;
}

/** Isi pengumpulan dari lastattempt.submission.plugins (mod_assign_get_submission_status). */
export function submissionContent(submission) {
  const plugins = submission?.plugins ?? [];
  const text = plugins.find((p) => p.type === 'onlinetext')?.editorfields?.find((f) => f.name === 'onlinetext')?.text ?? '';
  const files = plugins.find((p) => p.type === 'file')?.fileareas?.find((a) => a.area === 'submission_files')?.files ?? [];
  return { text, files };
}
