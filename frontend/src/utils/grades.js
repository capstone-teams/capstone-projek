// Item penilaian dari gradereport_user_get_grade_items (laporan nilai dosen dan mahasiswa).

export const gradeItemLabel = (item) => (item.itemtype === 'course' ? 'Total kursus' : item.itemname ?? '-');
export const gradeRange = (item) => `${Number(item.grademin ?? 0)}–${Number(item.grademax ?? 100)}`;
