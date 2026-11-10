/**
 * ID kursus di URL halaman kursus bisa berupa ID kursus Moodle (angka, dari /integrations/moodle/courses) atau ID
 * project kursus backend (shortuuid, dari /courses). Endpoint /courses/{id} hanya menerima ID backend, sehingga
 * kursus Moodle dibaca lewat /integrations/moodle/courses/{id} agar tidak memanggil endpoint yang pasti 404.
 */
export const isMoodleCourseId = (courseId) => /^\d+$/.test(String(courseId ?? ''));
