<?php
namespace local_capstonebridge\external;

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;
use local_capstonebridge\module_helper;
use local_capstonebridge\quiz_helper;

defined('MOODLE_INTERNAL') || die();

class create_quiz extends external_api {
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'Course id'),
            'section' => new external_value(PARAM_INT, 'Section number (0 is General)'),
            'name' => new external_value(PARAM_TEXT, 'Quiz name'),
            'intro' => new external_value(PARAM_RAW, 'Quiz description (HTML)', VALUE_DEFAULT, ''),
            'idnumber' => new external_value(
                PARAM_RAW_TRIMMED,
                'Idempotency key stored as the activity ID number and the question category ID number'
            ),
            'timelimit' => new external_value(PARAM_INT, 'Time limit in seconds, 0 for none', VALUE_DEFAULT, 0),
            'attempts' => new external_value(PARAM_INT, 'Attempts allowed, 0 for unlimited', VALUE_DEFAULT, 1),
            'passpercent' => new external_value(PARAM_INT, 'Passing grade in percent, 0 for none', VALUE_DEFAULT, 0),
            'shufflequestions' => new external_value(PARAM_INT, '1 to shuffle the question order', VALUE_DEFAULT, 0),
            'questions' => quiz_helper::questions_parameter(),
        ]);
    }

    public static function execute(
        int $courseid,
        int $section,
        string $name,
        string $intro,
        string $idnumber,
        int $timelimit = 0,
        int $attempts = 1,
        int $passpercent = 0,
        int $shufflequestions = 0,
        array $questions = []
    ): array {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/course/modlib.php');
        require_once($CFG->dirroot . '/mod/quiz/lib.php');
        require_once($CFG->dirroot . '/mod/quiz/locallib.php');
        require_once($CFG->libdir . '/questionlib.php');

        $params = self::validate_parameters(self::execute_parameters(), [
            'courseid' => $courseid,
            'section' => $section,
            'name' => $name,
            'intro' => $intro,
            'idnumber' => $idnumber,
            'timelimit' => $timelimit,
            'attempts' => $attempts,
            'passpercent' => $passpercent,
            'shufflequestions' => $shufflequestions,
            'questions' => $questions,
        ]);
        if ($params['idnumber'] === '') {
            throw new \invalid_parameter_exception('idnumber is required for quizzes');
        }
        quiz_helper::validate($params);

        $course = get_course($params['courseid']);
        $context = \context_course::instance($course->id);
        self::validate_context($context);
        require_capability('moodle/course:manageactivities', $context);
        require_capability('mod/quiz:addinstance', $context);

        $existing = module_helper::find_existing($course->id, 'quiz', $params['idnumber']);
        if ($existing !== null) {
            $count = $DB->count_records('quiz_slots', ['quizid' => $existing['instanceid']]);
            return module_helper::result($existing['cmid'], $existing['instanceid'], false) + ['questioncount' => $count];
        }

        $moduleinfo = (object) array_merge(quiz_helper::default_settings(), [
            'modulename' => 'quiz',
            'module' => $DB->get_field('modules', 'id', ['name' => 'quiz'], MUST_EXIST),
            'course' => $course->id,
            'section' => $params['section'],
            'visible' => 1,
            'name' => $params['name'],
            'introeditor' => ['text' => $params['intro'], 'format' => FORMAT_HTML, 'itemid' => 0],
            'cmidnumber' => $params['idnumber'],
        ]);
        quiz_helper::apply_config($moduleinfo, $params);

        $transaction = $DB->start_delegated_transaction();
        $created = add_moduleinfo($moduleinfo, $course);
        $cm = module_helper::require_module($course->id, (int) $created->coursemodule, 'quiz');
        $category = quiz_helper::quiz_category($course, $params['idnumber'], $params['name']);
        require_capability('moodle/question:add', \context::instance_by_id($category->contextid));
        $count = quiz_helper::replace_questions(
            $course,
            $cm,
            $category,
            $params['questions'],
            (bool) $params['shufflequestions']
        );
        $transaction->allow_commit();

        return module_helper::result((int) $cm->id, (int) $cm->instance, true) + ['questioncount' => $count];
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid' => new external_value(PARAM_INT, 'Course module id'),
            'instanceid' => new external_value(PARAM_INT, 'Quiz instance id'),
            'created' => new external_value(PARAM_INT, '1 if newly created, 0 if it already existed'),
            'questioncount' => new external_value(PARAM_INT, 'Number of questions in the quiz'),
        ]);
    }
}