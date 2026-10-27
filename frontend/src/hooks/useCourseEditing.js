import { useCallback, useContext, useState } from 'react';
import { AppStateContext } from '../context/appStateContext';
import { useMoodleCourse } from './useMoodleCourse';
import {
  CM_ACTION,
  SECTION_ACTION,
  createActivity,
  moveActivity,
  renameActivity,
  renameSection,
  updateCourseState,
} from '../services/moodle/courseEditing';

const CM_MESSAGES = {
  [CM_ACTION.HIDE]: 'Aktivitas disembunyikan dari mahasiswa.',
  [CM_ACTION.SHOW]: 'Aktivitas ditampilkan untuk mahasiswa.',
  [CM_ACTION.DUPLICATE]: 'Aktivitas diduplikat.',
  [CM_ACTION.DELETE]: 'Aktivitas dihapus.',
  [CM_ACTION.INDENT]: null,
  [CM_ACTION.OUTDENT]: null,
};

/**
 * Aksi Edit mode untuk satu kursus. Setiap aksi memuat ulang isi kursus dari Moodle
 * sehingga tampilan selalu mengikuti state server. `pending` berisi kunci aksi yang sedang berjalan.
 */
export function useCourseEditing() {
  const { course, reload } = useMoodleCourse();
  const notify = useContext(AppStateContext)?.notify;
  const [pending, setPending] = useState(null);
  const [error, setError] = useState(null);

  // onError: tampilkan error di tempat lain (mis. di dalam dialog) alih-alih di halaman.
  const run = useCallback(async (key, task, successMessage, onError) => {
    setPending(key);
    setError(null);
    try {
      // Hasil aksi (mis. { cmid } aktivitas baru) dikembalikan; aksi tanpa hasil mengembalikan true.
      const result = await task();
      await reload({ silent: true });
      if (successMessage) notify?.(successMessage, { type: 'success' });
      return result ?? true;
    } catch (e) {
      (onError ?? setError)(e);
      // Isi kursus mungkin sudah berubah di Moodle (mis. aktivitas dihapus di tab lain).
      await reload({ silent: true });
      return false;
    } finally {
      setPending(null);
    }
  }, [reload, notify]);

  return {
    pending,
    error,
    clearError: () => setError(null),
    cmAction: (cm, action) => run(`${action}:${cm.id}`, () => updateCourseState(course.id, action, [cm.id]), CM_MESSAGES[action]),
    moveCm: (cm, targetSectionId, targetCmId) =>
      run(`${CM_ACTION.MOVE}:${cm.id}`, () => moveActivity(course.id, cm.id, targetSectionId, targetCmId), 'Aktivitas dipindahkan.'),
    renameCm: (cm, name) => run(`rename:${cm.id}`, () => renameActivity(cm.id, name)),
    renameSection: (section, name) => run(`rename-section:${section.id}`, () => renameSection(course.format, section.id, name)),
    setSectionVisible: (section, visible) =>
      run(
        `section:${section.id}`,
        () => updateCourseState(course.id, visible ? SECTION_ACTION.SHOW : SECTION_ACTION.HIDE, [section.id]),
        visible ? 'Section ditampilkan untuk mahasiswa.' : 'Section disembunyikan dari mahasiswa.',
      ),
    addSection: () => run(SECTION_ACTION.ADD, () => updateCourseState(course.id, SECTION_ACTION.ADD), 'Section baru ditambahkan.'),
    createActivity: (section, modname, fields, successMessage, onError) =>
      run(`create:${section.id}`, () => createActivity(course.id, section.section, modname, fields), successMessage, onError),
  };
}
