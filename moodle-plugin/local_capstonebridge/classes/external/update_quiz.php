<?php
namespace local_capstonebridge\external;

use core_external\external_api;
use core_external\external_function_parameters;
use core_external\external_single_structure;
use core_external\external_value;
use local_capstonebridge\module_helper;
use local_capstonebridge\quiz_helper;

defined('MOODLE_INTERNAL') || die();

class update_quiz extends external_api {
    public static function execute_parameters(): external_function_parameters {
        return new external_function_parameters([
            'courseid' => new external_value(PARAM_INT, 'Course id'),
            'cmid' => new external_value(PARAM_INT, 'Course module id of the quiz'),
            'name' => new external_value(PARAM_TEXT, 'Quiz name'),
            'intro' => new external_value(PARAM_RAW, 'Quiz description (HTML)', VALUE_DEFAULT, ''),
            'timelimit' => new external_value(PARAM_INT, 'Time limit in seconds, 0 for none', VALUE_DEFAULT, 0),
            'attempts' => new external_value(PARAM_INT, 'Attempts allowed, 0 for unlimited', VALUE_DEFAULT, 1),
            'passpercent' => new external_value(PARAM_INT, 'Passing grade in percent, 0 for none', VALUE_DEFAULT, 0),
            'shufflequestions' => new external_value(PARAM_INT, '1 to shuffle the question order', VALUE_DEFAULT, 0),
            'questions' => quiz_helper::questions_parameter(),
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
        int $timelimit = 0,
        int $attempts = 1,
        int $passpercent = 0,
        int $shufflequestions = 0,
        array $questions = [],
        int $section = -1
    ): array {
        global $CFG, $DB;
        require_once($CFG->dirroot . '/course/modlib.php');
        require_once($CFG->dirroot . '/mod/quiz/lib.php');
        require_once($CFG->dirroot . '/mod/quiz/locallib.php');
        require_once($CFG->libdir . '/questionlib.php');

        $params = self::validate_parameters(self::execute_parameters(), [
            'courseid' => $courseid,
            'cmid' => $cmid,
            'name' => $name,
            'intro' => $intro,
            'timelimit' => $timelimit,
            'attempts' => $attempts,
            'passpercent' => $passpercent,
            'shufflequestions' => $shufflequestions,
            'questions' => $questions,
            'section' => $section,
        ]);
        quiz_helper::validate($params);

        $course = get_course($params['courseid']);
        $cm = module_helper::require_module($course->id, $params['cmid'], 'quiz');
        $context = \context_module::instance($cm->id);
        self::validate_context($context);
        require_capability('moodle/course:manageactivities', $context);
        require_capability('mod/quiz:manage', $context);
        if ($cm->idnumber === '') {
            throw new \invalid_parameter_exception('quiz was not created by Capstone Bridge (missing ID number)');
        }

        $transaction = $DB->start_delegated_transaction();
        [$cm, , , $data] = get_moduleinfo_data($cm, $course);
        foreach (quiz_helper::default_settings() as $field => $value) {
            if (!in_array($field, ['sumgrades', 'grade'], true)) {
                $data->$field = $value;
            }
        }
        $data->name = $params['name'];
        $data->introeditor = ['text' => $params['intro'], 'format' => FORMAT_HTML, 'itemid' => 0];
        quiz_helper::apply_config($data, $params);
        update_moduleinfo($cm, $data, $course);

        module_helper::move_to_section($course, $cm, $params['section']);
        $cm = module_helper::require_module($course->id, $cm->id, 'quiz');

        // Soal hanya diganti bila belum ada attempt, agar jawaban dan nilai mahasiswa tidak rusak.
        $hasattempts = quiz_has_attempts($cm->instance);
        $replaced = false;
        if (!$hasattempts) {
            $category = quiz_helper::quiz_category($course, $cm->idnumber, $params['name']);
            require_capability('moodle/question:add', \context::instance_by_id($category->contextid));
            quiz_helper::replace_questions(
                $course,
                $cm,
                $category,
                $params['questions'],
                (bool) $params['shufflequestions']
            );
            $replaced = true;
        }
        $transaction->allow_commit();

        return module_helper::update_result((int) $cm->id, (int) $cm->instance, (int) $cm->sectionnum) + [
            'hasattempts' => $hasattempts ? 1 : 0,
            'questionsreplaced' => $replaced ? 1 : 0,
            'questioncount' => $DB->count_records('quiz_slots', ['quizid' => $cm->instance]),
        ];
    }

    public static function execute_returns(): external_single_structure {
        return new external_single_structure([
            'cmid' => new external_value(PARAM_INT, 'Course module id'),
            'instanceid' => new external_value(PARAM_INT, 'Quiz instance id'),
            'section' => new external_value(PARAM_INT, 'Section number after the update'),
            'updated' => new external_value(PARAM_INT, '1 when the quiz was updated'),
            'hasattempts' => new external_value(PARAM_INT, '1 when students have already attempted the quiz'),
            'questionsreplaced' => new external_value(
                PARAM_INT,
                '1 when the questions were replaced, 0 when kept because of existing attempts'
            ),
            'questioncount' => new external_value(PARAM_INT, 'Number of questions in the quiz'),
        ]);
    }
}