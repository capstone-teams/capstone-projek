<?php
namespace local_capstonebridge\external;

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;
use local_capstonebridge\module_helper;

defined('MOODLE_INTERNAL') || die();

class create_url extends external_api {
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'Course id'),
            'section' => new external_value(PARAM_INT, 'Section number (0 is General)'),
            'name' => new external_value(PARAM_TEXT, 'Resource name'),
            'externalurl' => new external_value(PARAM_URL, 'Absolute http(s) URL of the resource'),
            'intro' => new external_value(PARAM_RAW, 'Resource description (HTML)', VALUE_DEFAULT, ''),
            'idnumber' => new external_value(
                PARAM_RAW_TRIMMED,
                'Idempotency key stored as the activity ID number',
                VALUE_DEFAULT,
                ''
            ),
        ]);
    }

    public static function execute(
        int $courseid,
        int $section,
        string $name,
        string $externalurl,
        string $intro = '',
        string $idnumber = ''
    ): array {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/course/modlib.php');
        require_once($CFG->libdir . '/resourcelib.php');

        $params = self::validate_parameters(self::execute_parameters(), [
            'courseid' => $courseid,
            'section' => $section,
            'name' => $name,
            'externalurl' => $externalurl,
            'intro' => $intro,
            'idnumber' => $idnumber,
        ]);
        if ($params['externalurl'] === '') {
            throw new \invalid_parameter_exception('externalurl must be a valid http(s) URL');
        }

        $course = get_course($params['courseid']);
        $context = \context_course::instance($course->id);
        self::validate_context($context);
        require_capability('moodle/course:manageactivities', $context);
        require_capability('mod/url:addinstance', $context);

        $existing = module_helper::find_existing($course->id, 'url', $params['idnumber']);
        if ($existing !== null) {
            return module_helper::result($existing['cmid'], $existing['instanceid'], false);
        }

        $moduleinfo = (object) [
            'modulename' => 'url',
            'module' => $DB->get_field('modules', 'id', ['name' => 'url'], MUST_EXIST),
            'course' => $course->id,
            'section' => $params['section'],
            'visible' => 1,
            'name' => $params['name'],
            'introeditor' => [
                'text' => $params['intro'],
                'format' => FORMAT_HTML,
                'itemid' => 0,
            ],
            'externalurl' => $params['externalurl'],
            'display' => RESOURCELIB_DISPLAY_AUTO,
            'printintro' => 1,
            'cmidnumber' => $params['idnumber'],
        ];

        $created = add_moduleinfo($moduleinfo, $course);

        return module_helper::result((int) $created->coursemodule, (int) $created->instance, true);
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid' => new external_value(PARAM_INT, 'Course module id'),
            'instanceid' => new external_value(PARAM_INT, 'URL instance id'),
            'created' => new external_value(PARAM_INT, '1 if newly created, 0 if it already existed'),
        ]);
    }
}