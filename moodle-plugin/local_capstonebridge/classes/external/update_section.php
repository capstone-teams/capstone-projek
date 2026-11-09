<?php
namespace local_capstonebridge\external;

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;

defined('MOODLE_INTERNAL') || die();

/**
 * Perbarui nama dan ringkasan (summary) satu section course.
 *
 * Moodle core hanya menyediakan rename section lewat web service
 * (core_update_inplace_editable); ringkasan section tidak dapat diubah tanpa
 * function ini. Section dicari berdasarkan id dan harus milik course yang diberikan.
 */
class update_section extends external_api {
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'Course id'),
            'sectionid' => new external_value(PARAM_INT, 'Section id (course_sections.id)'),
            'name' => new external_value(PARAM_TEXT, 'Section name'),
            'summary' => new external_value(PARAM_RAW, 'Section summary in HTML', VALUE_DEFAULT, ''),
        ]);
    }

    public static function execute(int $courseid, int $sectionid, string $name, string $summary = ''): array {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/course/lib.php');

        $params = self::validate_parameters(self::execute_parameters(), [
            'courseid' => $courseid,
            'sectionid' => $sectionid,
            'name' => $name,
            'summary' => $summary,
        ]);

        $course = get_course($params['courseid']);
        $context = \context_course::instance($course->id);
        self::validate_context($context);
        require_capability('moodle/course:update', $context);

        $section = $DB->get_record(
            'course_sections',
            ['id' => $params['sectionid'], 'course' => $course->id],
            '*',
            MUST_EXIST
        );
        $name = trim($params['name']);
        if ($name === '' || \core_text::strlen($name) > 255) {
            throw new \invalid_parameter_exception('Section name must be between 1 and 255 characters');
        }

        course_update_section($course, $section, [
            'name' => $name,
            'summary' => $params['summary'],
            'summaryformat' => FORMAT_HTML,
        ]);

        return [
            'sectionid' => (int) $section->id,
            'section' => (int) $section->section,
            'name' => $name,
            'updated' => 1,
        ];
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'sectionid' => new external_value(PARAM_INT, 'Section id'),
            'section' => new external_value(PARAM_INT, 'Section number'),
            'name' => new external_value(PARAM_TEXT, 'Section name after the update'),
            'updated' => new external_value(PARAM_INT, '1 when the section was updated'),
        ]);
    }
}