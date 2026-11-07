<?php
namespace local_capstonebridge\external;

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;
use local_capstonebridge\module_helper;

defined('MOODLE_INTERNAL') || die();

class update_page extends external_api {
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'Course id'),
            'cmid' => new external_value(PARAM_INT, 'Course module id of the page'),
            'name' => new external_value(PARAM_TEXT, 'Page name'),
            'content' => new external_value(PARAM_RAW, 'Page HTML content'),
            'intro' => new external_value(PARAM_RAW, 'Page description', VALUE_DEFAULT, ''),
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
        string $content,
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
            'content' => $content,
            'intro' => $intro,
            'section' => $section,
        ]);

        $course = get_course($params['courseid']);
        $cm = module_helper::require_module($course->id, $params['cmid'], 'page');
        $context = \context_module::instance($cm->id);
        self::validate_context($context);
        require_capability('moodle/course:manageactivities', $context);

        [$cm, , , $data] = get_moduleinfo_data($cm, $course);
        module_helper::apply_display_options($data);
        $data->name = $params['name'];
        $data->introeditor = ['text' => $params['intro'], 'format' => FORMAT_HTML, 'itemid' => 0];
        $data->page = ['text' => $params['content'], 'format' => FORMAT_HTML, 'itemid' => 0];
        update_moduleinfo($cm, $data, $course);

        module_helper::move_to_section($course, $cm, $params['section']);
        $cm = module_helper::require_module($course->id, $cm->id, 'page');

        return module_helper::update_result((int) $cm->id, (int) $cm->instance, (int) $cm->sectionnum);
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid' => new external_value(PARAM_INT, 'Course module id'),
            'instanceid' => new external_value(PARAM_INT, 'Page instance id'),
            'section' => new external_value(PARAM_INT, 'Section number after the update'),
            'updated' => new external_value(PARAM_INT, '1 when the page was updated'),
        ]);
    }
}