<?php
namespace local_capstonebridge\external;

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;
use local_capstonebridge\module_helper;

defined('MOODLE_INTERNAL') || die();

class update_assign extends external_api {
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'Course id'),
            'cmid' => new external_value(PARAM_INT, 'Course module id of the assignment'),
            'name' => new external_value(PARAM_TEXT, 'Assignment name'),
            'intro' => new external_value(PARAM_RAW, 'Assignment description (HTML)', VALUE_DEFAULT, ''),
            'duedate' => new external_value(PARAM_INT, 'Due date as unix timestamp, 0 for none', VALUE_DEFAULT, 0),
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
        string $intro = '',
        int $duedate = 0,
        int $section = -1
    ): array {
        global $CFG;
        require_once($CFG->dirroot . '/course/modlib.php');
        require_once($CFG->dirroot . '/mod/assign/locallib.php');

        $params = self::validate_parameters(self::execute_parameters(), [
            'courseid' => $courseid,
            'cmid' => $cmid,
            'name' => $name,
            'intro' => $intro,
            'duedate' => $duedate,
            'section' => $section,
        ]);

        $course = get_course($params['courseid']);
        $cm = module_helper::require_module($course->id, $params['cmid'], 'assign');
        $context = \context_module::instance($cm->id);
        self::validate_context($context);
        require_capability('moodle/course:manageactivities', $context);

        [$cm, , , $data] = get_moduleinfo_data($cm, $course);

        // Pertahankan status plugin submission/feedback; tanpa ini update akan menonaktifkannya.
        $assign = new \assign($context, $cm, $course);
        foreach ($assign->get_submission_plugins() as $plugin) {
            $data->{'assignsubmission_' . $plugin->get_type() . '_enabled'} = $plugin->is_enabled() ? 1 : 0;
        }
        foreach ($assign->get_feedback_plugins() as $plugin) {
            $data->{'assignfeedback_' . $plugin->get_type() . '_enabled'} = $plugin->is_enabled() ? 1 : 0;
        }

        $data->name = $params['name'];
        $data->introeditor = ['text' => $params['intro'], 'format' => FORMAT_HTML, 'itemid' => 0];
        $data->duedate = $params['duedate'];
        update_moduleinfo($cm, $data, $course);

        module_helper::move_to_section($course, $cm, $params['section']);
        $cm = module_helper::require_module($course->id, $cm->id, 'assign');

        return module_helper::update_result((int) $cm->id, (int) $cm->instance, (int) $cm->sectionnum);
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid' => new external_value(PARAM_INT, 'Course module id'),
            'instanceid' => new external_value(PARAM_INT, 'Assignment instance id'),
            'section' => new external_value(PARAM_INT, 'Section number after the update'),
            'updated' => new external_value(PARAM_INT, '1 when the assignment was updated'),
        ]);
    }
}