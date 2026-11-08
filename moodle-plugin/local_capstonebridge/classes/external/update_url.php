<?php
namespace local_capstonebridge\external;

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;
use local_capstonebridge\module_helper;

defined('MOODLE_INTERNAL') || die();

class update_url extends external_api {
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'Course id'),
            'cmid' => new external_value(PARAM_INT, 'Course module id of the URL resource'),
            'name' => new external_value(PARAM_TEXT, 'Resource name'),
            'externalurl' => new external_value(PARAM_URL, 'Absolute http(s) URL of the resource'),
            'intro' => new external_value(PARAM_RAW, 'Resource description (HTML)', VALUE_DEFAULT, ''),
            'section' => new external_value(
                PARAM_INT,
                'Target section number, -1 keeps the current section',
                VALUE_DEFAULT,
                -1
            ),
        ]);
    }

    public static function execute(
        int $courseid,
        int $cmid,
        string $name,
        string $externalurl,
        string $intro = '',
        int $section = -1
    ): array {
        global $CFG;
        require_once($CFG->dirroot . '/course/modlib.php');
        require_once($CFG->libdir . '/resourcelib.php');

        $params = self::validate_parameters(self::execute_parameters(), [
            'courseid' => $courseid,
            'cmid' => $cmid,
            'name' => $name,
            'externalurl' => $externalurl,
            'intro' => $intro,
            'section' => $section,
        ]);
        if ($params['externalurl'] === '') {
            throw new \invalid_parameter_exception('externalurl must be a valid http(s) URL');
        }

        $course = get_course($params['courseid']);
        $cm = module_helper::require_module($course->id, $params['cmid'], 'url');
        $context = \context_module::instance($cm->id);
        self::validate_context($context);
        require_capability('moodle/course:manageactivities', $context);

        [$cm, , , $data] = get_moduleinfo_data($cm, $course);
        module_helper::apply_display_options($data);
        $data->name = $params['name'];
        $data->introeditor = ['text' => $params['intro'], 'format' => FORMAT_HTML, 'itemid' => 0];
        $data->externalurl = $params['externalurl'];
        update_moduleinfo($cm, $data, $course);

        module_helper::move_to_section($course, $cm, $params['section']);
        $cm = module_helper::require_module($course->id, $cm->id, 'url');

        return module_helper::update_result((int) $cm->id, (int) $cm->instance, (int) $cm->sectionnum);
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid' => new external_value(PARAM_INT, 'Course module id'),
            'instanceid' => new external_value(PARAM_INT, 'URL instance id'),
            'section' => new external_value(PARAM_INT, 'Section number after the update'),
            'updated' => new external_value(PARAM_INT, '1 when the resource was updated'),
        ]);
    }
}