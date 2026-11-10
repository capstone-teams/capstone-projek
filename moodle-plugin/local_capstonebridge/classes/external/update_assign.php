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
            'grade' => new external_value(PARAM_INT, 'Maximum grade (point), -1 keeps the current value', VALUE_DEFAULT, -1),
            'onlinetext' => new external_value(
                PARAM_INT,
                '1/0 to enable/disable online text submission, -1 keeps the current value',
                VALUE_DEFAULT,
                -1
            ),
            'filesubmission' => new external_value(
                PARAM_INT,
                '1/0 to enable/disable file submission, -1 keeps the current value',
                VALUE_DEFAULT,
                -1
            ),
            'maxfiles' => new external_value(
                PARAM_INT,
                'Maximum number of uploaded files, -1 keeps the current value',
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
        int $section = -1,
        int $grade = -1,
        int $onlinetext = -1,
        int $filesubmission = -1,
        int $maxfiles = -1
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
            'grade' => $grade,
            'onlinetext' => $onlinetext,
            'filesubmission' => $filesubmission,
            'maxfiles' => $maxfiles,
        ]);
        module_helper::validate_assign_settings(
            $params['grade'],
            $params['onlinetext'],
            $params['filesubmission'],
            $params['maxfiles']
        );

        $course = get_course($params['courseid']);
        $cm = module_helper::require_module($course->id, $params['cmid'], 'assign');
        $context = \context_module::instance($cm->id);
        self::validate_context($context);
        require_capability('moodle/course:manageactivities', $context);

        [$cm, , , $data] = get_moduleinfo_data($cm, $course);

        // Pertahankan status dan setting plugin submission/feedback; tanpa ini
        // update_moduleinfo() akan menonaktifkan atau mengosongkannya.
        $assign = new \assign($context, $cm, $course);
        foreach ($assign->get_submission_plugins() as $plugin) {
            $data->{'assignsubmission_' . $plugin->get_type() . '_enabled'} = $plugin->is_enabled() ? 1 : 0;
        }
        foreach ($assign->get_feedback_plugins() as $plugin) {
            $data->{'assignfeedback_' . $plugin->get_type() . '_enabled'} = $plugin->is_enabled() ? 1 : 0;
        }
        $fileplugin = $assign->get_submission_plugin_by_type('file');
        $data->assignsubmission_file_maxfiles = (int) ($fileplugin->get_config('maxfilesubmissions') ?: 1);
        $data->assignsubmission_file_maxsizebytes = (int) $fileplugin->get_config('maxsubmissionsizebytes');
        $data->assignsubmission_file_filetypes = (string) $fileplugin->get_config('filetypeslist');

        $data->name = $params['name'];
        $data->introeditor = ['text' => $params['intro'], 'format' => FORMAT_HTML, 'itemid' => 0];
        $data->duedate = $params['duedate'];
        if ($params['grade'] > 0) {
            $data->grade = $params['grade'];
        }
        if ($params['onlinetext'] >= 0) {
            $data->assignsubmission_onlinetext_enabled = $params['onlinetext'];
        }
        if ($params['filesubmission'] >= 0) {
            $data->assignsubmission_file_enabled = $params['filesubmission'];
        }
        if ($params['maxfiles'] > 0) {
            $data->assignsubmission_file_maxfiles = $params['maxfiles'];
        }
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