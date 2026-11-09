<?php
namespace local_capstonebridge\external;

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;
use local_capstonebridge\module_helper;

defined('MOODLE_INTERNAL') || die();

class create_assign extends external_api {
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'Course id'),
            'section' => new external_value(PARAM_INT, 'Section number (0 is General)'),
            'name' => new external_value(PARAM_TEXT, 'Assignment name'),
            'intro' => new external_value(PARAM_RAW, 'Assignment description (HTML)', VALUE_DEFAULT, ''),
            'duedate' => new external_value(PARAM_INT, 'Due date as unix timestamp, 0 for none', VALUE_DEFAULT, 0),
            'idnumber' => new external_value(
                PARAM_RAW_TRIMMED,
                'Idempotency key stored as the activity ID number',
                VALUE_DEFAULT,
                ''
            ),
            'grade' => new external_value(PARAM_INT, 'Maximum grade (point)', VALUE_DEFAULT, 100),
            'onlinetext' => new external_value(PARAM_INT, '1 to enable online text submission', VALUE_DEFAULT, 1),
            'filesubmission' => new external_value(PARAM_INT, '1 to enable file submission', VALUE_DEFAULT, 0),
            'maxfiles' => new external_value(PARAM_INT, 'Maximum number of uploaded files', VALUE_DEFAULT, 1),
        ]);
    }

    public static function execute(
        int $courseid,
        int $section,
        string $name,
        string $intro = '',
        int $duedate = 0,
        string $idnumber = '',
        int $grade = 100,
        int $onlinetext = 1,
        int $filesubmission = 0,
        int $maxfiles = 1
    ): array {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/course/modlib.php');

        $params = self::validate_parameters(self::execute_parameters(), [
            'courseid' => $courseid,
            'section' => $section,
            'name' => $name,
            'intro' => $intro,
            'duedate' => $duedate,
            'idnumber' => $idnumber,
            'grade' => $grade,
            'onlinetext' => $onlinetext,
            'filesubmission' => $filesubmission,
            'maxfiles' => $maxfiles,
        ]);
        if ($params['grade'] < 0 || $params['onlinetext'] < 0 || $params['filesubmission'] < 0 || $params['maxfiles'] < 0) {
            throw new \invalid_parameter_exception('grade, onlinetext, filesubmission, and maxfiles cannot be negative');
        }
        module_helper::validate_assign_settings(
            $params['grade'],
            $params['onlinetext'],
            $params['filesubmission'],
            $params['maxfiles']
        );

        $course = get_course($params['courseid']);
        $context = \context_course::instance($course->id);
        self::validate_context($context);
        require_capability('moodle/course:manageactivities', $context);
        require_capability('mod/assign:addinstance', $context);

        $existing = module_helper::find_existing($course->id, 'assign', $params['idnumber']);
        if ($existing !== null) {
            return module_helper::result($existing['cmid'], $existing['instanceid'], false);
        }

        $moduleinfo = (object) [
            'modulename' => 'assign',
            'module' => $DB->get_field('modules', 'id', ['name' => 'assign'], MUST_EXIST),
            'course' => $course->id,
            'section' => $params['section'],
            'visible' => 1,
            'name' => $params['name'],
            'introeditor' => [
                'text' => $params['intro'],
                'format' => FORMAT_HTML,
                'itemid' => 0
            ],
            'cmidnumber' => $params['idnumber'],
            'alwaysshowdescription' => 1,
            'submissiondrafts' => 0,
            'requiresubmissionstatement' => 0,
            'sendnotifications' => 0,
            'sendlatenotifications' => 0,
            'sendstudentnotifications' => 1,
            'duedate' => $params['duedate'],
            'cutoffdate' => 0,
            'gradingduedate' => 0,
            'allowsubmissionsfromdate' => 0,
            'grade' => $params['grade'],
            'teamsubmission' => 0,
            'requireallteammemberssubmit' => 0,
            'blindmarking' => 0,
            'hidegrader' => 0,
            'markingworkflow' => 0,
            'markingallocation' => 0,
            'preventsubmissionnotingroup' => 0,
            'maxattempts' => -1,
            'attemptreopenmethod' => 'none',
            'completionsubmit' => 0,
            'assignsubmission_onlinetext_enabled' => $params['onlinetext'],
            'assignsubmission_file_enabled' => $params['filesubmission'],
            'assignsubmission_file_maxfiles' => $params['maxfiles'],
            'assignsubmission_file_maxsizebytes' => 0,
            'assignsubmission_file_filetypes' => '',
            'assignfeedback_comments_enabled' => 1,
        ];

        $created = add_moduleinfo($moduleinfo, $course);

        return module_helper::result((int) $created->coursemodule, (int) $created->instance, true);
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid' => new external_value(PARAM_INT, 'Course module id'),
            'instanceid' => new external_value(PARAM_INT, 'Assignment instance id'),
            'created' => new external_value(PARAM_INT, '1 if newly created, 0 if it already existed'),
        ]);
    }
}