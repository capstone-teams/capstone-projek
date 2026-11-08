<?php
namespace local_capstonebridge;

defined('MOODLE_INTERNAL') || die();

class module_helper {
    /**
     * Cari activity pada course berdasarkan ID number (idempotency key).
     */
    public static function find_existing(int $courseid, string $modulename, string $idnumber): ?array {
        global $DB;

        if ($idnumber === '') {
            return null;
        }

        $sql = "SELECT cm.id AS cmid, cm.instance AS instanceid
                  FROM {course_modules} cm
                  JOIN {modules} m ON m.id = cm.module
                 WHERE cm.course = :courseid
                   AND m.name = :modulename
                   AND cm.idnumber = :idnumber
                   AND cm.deletioninprogress = 0";
        $record = $DB->get_record_sql($sql, [
            'courseid' => $courseid,
            'modulename' => $modulename,
            'idnumber' => $idnumber,
        ], IGNORE_MULTIPLE);

        if (!$record) {
            return null;
        }

        return ['cmid' => (int) $record->cmid, 'instanceid' => (int) $record->instanceid];
    }

    /**
     * Ambil course module milik course tertentu dengan jenis module yang sesuai.
     * Melempar exception bila cmid bukan milik course atau jenisnya berbeda.
     */
    public static function require_module(int $courseid, int $cmid, string $modulename): \stdClass {
        $cm = get_coursemodule_from_id($modulename, $cmid, $courseid, true, MUST_EXIST);
        if (!empty($cm->deletioninprogress)) {
            throw new \moodle_exception('invalidcoursemodule');
        }
        return $cm;
    }

    /**
     * Pindahkan activity ke nomor section lain bila berbeda. Section yang belum ada dibuat dulu.
     * Nilai negatif berarti section tidak diubah.
     */
    public static function move_to_section(\stdClass $course, \stdClass $cm, int $sectionnumber): void {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/course/lib.php');

        if ($sectionnumber < 0 || (int) $cm->sectionnum === $sectionnumber) {
            return;
        }

        course_create_sections_if_missing($course, $sectionnumber);
        $section = $DB->get_record(
            'course_sections',
            ['course' => $course->id, 'section' => $sectionnumber],
            '*',
            MUST_EXIST
        );
        moveto_module($cm, $section);
    }

    /**
     * Isi ulang field form yang tidak tersimpan apa adanya di tabel module
     * (display options) agar update_moduleinfo() tidak mengubahnya tanpa sengaja.
     */
    public static function apply_display_options(\stdClass $data): void {
        $options = empty($data->displayoptions) ? [] : (array) unserialize_array($data->displayoptions);
        $data->printintro = $options['printintro'] ?? 0;
        $data->printlastmodified = $options['printlastmodified'] ?? 1;
        $data->popupwidth = $options['popupwidth'] ?? 620;
        $data->popupheight = $options['popupheight'] ?? 450;
    }

    public static function result(int $cmid, int $instanceid, bool $created): array {
        return [
            'cmid' => $cmid,
            'instanceid' => $instanceid,
            'created' => $created ? 1 : 0,
        ];
    }

    public static function update_result(int $cmid, int $instanceid, int $section): array {
        return [
            'cmid' => $cmid,
            'instanceid' => $instanceid,
            'section' => $section,
            'updated' => 1,
        ];
    }
}