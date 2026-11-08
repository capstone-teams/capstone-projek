<?php
namespace local_capstonebridge;

defined('MOODLE_INTERNAL') || die();

/**
 * Helper Quiz: pengaturan dasar, question bank course, dan soal pilihan ganda.
 *
 * Soal disimpan pada question bank course dalam satu kategori per quiz. Kategori
 * memakai idempotency key quiz sebagai ID number, sehingga soal quiz yang sama
 * selalu berada di kategori yang sama dan dapat diganti tanpa membuat duplikat.
 *
 * - Moodle 5.0+: question bank course adalah activity Question bank bawaan
 *   (mod_qbank tipe system) yang dibuat otomatis bila belum ada.
 * - Moodle 4.5: question bank course adalah kategori soal pada context course.
 */
class quiz_helper {
    /** Nilai maksimum quiz (skala 0–100). */
    public const QUIZ_GRADE = 100;

    /**
     * Pengaturan tetap quiz yang dibuat plugin. Sama dengan nilai bawaan form Moodle,
     * kecuali review: mahasiswa dapat melihat jawaban, nilai, dan pembahasan setelah submit.
     */
    public static function default_settings(): array {
        $settings = [
            'timeopen' => 0,
            'timeclose' => 0,
            'preferredbehaviour' => 'deferredfeedback',
            'attemptonlast' => 0,
            'grademethod' => QUIZ_GRADEHIGHEST,
            'decimalpoints' => 2,
            'questiondecimalpoints' => -1,
            'questionsperpage' => 1,
            'navmethod' => QUIZ_NAVMETHOD_FREE,
            'shuffleanswers' => 1,
            'sumgrades' => 0,
            'grade' => self::QUIZ_GRADE,
            'overduehandling' => 'autosubmit',
            'graceperiod' => 0,
            'quizpassword' => '',
            'subnet' => '',
            'browsersecurity' => '-',
            'delay1' => 0,
            'delay2' => 0,
            'showuserpicture' => 0,
            'showblocks' => 0,
            'completionattemptsexhausted' => 0,
            'completionminattempts' => 0,
        ];
        $fields = ['attempt', 'correctness', 'maxmarks', 'marks', 'specificfeedback', 'generalfeedback',
            'rightanswer', 'overallfeedback'];
        foreach ($fields as $field) {
            $settings[$field . 'during'] = 0;
            foreach (['immediately', 'open', 'closed'] as $when) {
                $settings[$field . $when] = 1;
            }
        }
        return $settings;
    }

    /**
     * Terapkan konfigurasi dari backend (Content Schema §19) ke data module quiz.
     */
    public static function apply_config(\stdClass $data, array $params): void {
        $data->timelimit = max(0, (int) $params['timelimit']);
        $data->attempts = max(0, (int) $params['attempts']);
        $data->gradepass = $params['passpercent'] > 0
            ? round(self::QUIZ_GRADE * $params['passpercent'] / 100, 2)
            : 0;
    }

    /**
     * Validasi parameter konfigurasi dan soal sebelum menyentuh Moodle.
     */
    public static function validate(array $params): void {
        if ($params['timelimit'] < 0) {
            throw new \invalid_parameter_exception('timelimit cannot be negative');
        }
        if ($params['attempts'] < 0) {
            throw new \invalid_parameter_exception('attempts cannot be negative');
        }
        if ($params['passpercent'] < 0 || $params['passpercent'] > 100) {
            throw new \invalid_parameter_exception('passpercent must be between 0 and 100');
        }
        if ($params['shufflequestions'] < 0 || $params['shufflequestions'] > 1) {
            throw new \invalid_parameter_exception('shufflequestions must be 0 or 1');
        }
        if (empty($params['questions'])) {
            throw new \invalid_parameter_exception('quiz must have at least one question');
        }
        foreach ($params['questions'] as $index => $question) {
            $number = $index + 1;
            if (trim(strip_tags($question['text'])) === '') {
                throw new \invalid_parameter_exception("question {$number} has no text");
            }
            if (count($question['answers']) < 2) {
                throw new \invalid_parameter_exception("question {$number} needs at least two answers");
            }
            $correct = 0;
            foreach ($question['answers'] as $answer) {
                if (trim($answer['text']) === '') {
                    throw new \invalid_parameter_exception("question {$number} has an empty answer");
                }
                $correct += $answer['correct'] ? 1 : 0;
            }
            if ($correct !== 1) {
                throw new \invalid_parameter_exception("question {$number} must have exactly one correct answer");
            }
        }
    }

    /**
     * Context question bank course. Moodle 5.0+ memakai activity Question bank bawaan course.
     */
    public static function bank_context(\stdClass $course): \context {
        $helper = '\core_question\local\bank\question_bank_helper';
        if (class_exists($helper) && method_exists($helper, 'get_default_open_instance_system_type')) {
            $bank = $helper::get_default_open_instance_system_type($course, true);
            return \context_module::instance($bank->id);
        }
        return \context_course::instance($course->id);
    }

    /**
     * Kategori soal milik satu quiz, dibuat bila belum ada.
     */
    public static function quiz_category(\stdClass $course, string $idnumber, string $name): \stdClass {
        global $DB;

        $context = self::bank_context($course);
        $category = $DB->get_record('question_categories', ['contextid' => $context->id, 'idnumber' => $idnumber]);
        if ($category) {
            if ($category->name !== $name) {
                $DB->set_field('question_categories', 'name', $name, ['id' => $category->id]);
                $category->name = $name;
            }
            return $category;
        }

        $top = question_get_top_category($context->id, true);
        $category = (object) [
            'name' => $name,
            'contextid' => $context->id,
            'info' => 'Soal quiz yang dibuat oleh Capstone Bridge.',
            'infoformat' => FORMAT_HTML,
            'stamp' => make_unique_id_code(),
            'parent' => $top->id,
            'sortorder' => 999,
            'idnumber' => $idnumber,
        ];
        $category->id = $DB->insert_record('question_categories', $category);
        return $category;
    }

    /**
     * Ganti seluruh soal quiz dengan daftar soal baru.
     *
     * Hanya dipanggil bila quiz belum memiliki attempt, sehingga soal lama aman dihapus.
     *
     * @return int jumlah soal pada quiz setelah diganti
     */
    public static function replace_questions(\stdClass $course, \stdClass $cm, \stdClass $category,
            array $questions, bool $shuffle): int {
        global $CFG, $DB, $USER;
        require_once($CFG->dirroot . '/mod/quiz/locallib.php');
        require_once($CFG->libdir . '/questionlib.php');

        $quiz = $DB->get_record('quiz', ['id' => $cm->instance], '*', MUST_EXIST);
        $quiz->cmid = $cm->id;

        $structure = \mod_quiz\quiz_settings::create($quiz->id)->get_structure();
        $slots = $DB->get_records('quiz_slots', ['quizid' => $quiz->id], 'slot DESC');
        foreach ($slots as $slot) {
            $structure->remove_slot($slot->slot);
        }

        $old = $DB->get_records_sql(
            "SELECT DISTINCT qv.questionid
               FROM {question_bank_entries} qbe
               JOIN {question_versions} qv ON qv.questionbankentryid = qbe.id
              WHERE qbe.questioncategoryid = ?",
            [$category->id]
        );
        foreach ($old as $record) {
            question_delete_question($record->questionid);
        }

        $context = \context::instance_by_id($category->contextid);
        $qtype = \question_bank::get_qtype('multichoice');
        foreach (array_values($questions) as $index => $data) {
            $question = (object) [
                'category' => $category->id,
                'qtype' => 'multichoice',
                'createdby' => $USER->id,
                'idnumber' => null,
            ];
            $saved = $qtype->save_question($question, self::question_form($category, $context, $index, $data));
            quiz_add_quiz_question($saved->id, $quiz, 0, 1);
        }

        $DB->set_field('quiz_sections', 'shufflequestions', $shuffle ? 1 : 0, ['quizid' => $quiz->id]);
        \mod_quiz\quiz_settings::create($quiz->id)->get_grade_calculator()->recompute_quiz_sumgrades();

        return $DB->count_records('quiz_slots', ['quizid' => $quiz->id]);
    }

    /**
     * Data form soal pilihan ganda (satu jawaban benar), dalam bentuk yang diterima save_question().
     */
    private static function question_form(\stdClass $category, \context $context, int $index,
            array $data): \stdClass {
        $answers = array_values($data['answers']);
        $plain = trim(strip_tags($data['text']));
        $name = \core_text::substr('Soal ' . ($index + 1) . ' - ' . $plain, 0, 250);

        return (object) [
            'category' => $category->id . ',' . $context->id,
            'name' => $name,
            'idnumber' => '',
            'questiontext' => ['text' => $data['text'], 'format' => FORMAT_HTML],
            'generalfeedback' => ['text' => $data['generalfeedback'], 'format' => FORMAT_HTML],
            'defaultmark' => 1,
            'penalty' => 0.3333333,
            'status' => \core_question\local\bank\question_version_status::QUESTION_STATUS_READY,
            'single' => 1,
            'shuffleanswers' => 1,
            'answernumbering' => 'ABCD',
            'showstandardinstruction' => 0,
            'shownumcorrect' => 0,
            'correctfeedback' => ['text' => '', 'format' => FORMAT_HTML],
            'partiallycorrectfeedback' => ['text' => '', 'format' => FORMAT_HTML],
            'incorrectfeedback' => ['text' => '', 'format' => FORMAT_HTML],
            'noanswers' => count($answers),
            'answer' => array_map(static fn($a) => ['text' => $a['text'], 'format' => FORMAT_PLAIN], $answers),
            'fraction' => array_map(static fn($a) => $a['correct'] ? '1.0' : '0.0', $answers),
            'feedback' => array_map(static fn($a) => ['text' => '', 'format' => FORMAT_HTML], $answers),
            'hint' => [],
        ];
    }

    /**
     * Struktur parameter soal untuk external function.
     */
    public static function questions_parameter(): \core_external\external_multiple_structure {
        return new \core_external\external_multiple_structure(
            new \core_external\external_single_structure([
                'text' => new \core_external\external_value(PARAM_RAW, 'Question text (HTML)'),
                'generalfeedback' => new \core_external\external_value(
                    PARAM_RAW,
                    'Explanation shown after the attempt (HTML)',
                    VALUE_DEFAULT,
                    ''
                ),
                'answers' => new \core_external\external_multiple_structure(
                    new \core_external\external_single_structure([
                        'text' => new \core_external\external_value(PARAM_TEXT, 'Answer text'),
                        'correct' => new \core_external\external_value(PARAM_BOOL, 'Whether this answer is correct'),
                    ])
                ),
            ]),
            'Multiple choice questions with exactly one correct answer'
        );
    }
}