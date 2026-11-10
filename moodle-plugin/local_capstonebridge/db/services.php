
<?php
defined('MOODLE_INTERNAL') || die();

$functions = [
    'local_capstonebridge_create_page' => [
        'classname' => 'local_capstonebridge\external\create_page',
        'description' => 'Creates a Page activity in a course section.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:manageactivities,mod/page:addinstance',
    ],
    'local_capstonebridge_update_page' => [
        'classname' => 'local_capstonebridge\external\update_page',
        'description' => 'Updates the name, content, description, and section of a Page activity.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:manageactivities',
    ],
    'local_capstonebridge_create_assign' => [
        'classname' => 'local_capstonebridge\external\create_assign',
        'description' => 'Creates an Assignment activity in a course section with grade and submission settings.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:manageactivities,mod/assign:addinstance',
    ],
    'local_capstonebridge_update_assign' => [
        'classname' => 'local_capstonebridge\external\update_assign',
        'description' => 'Updates the name, description, due date, and section of an Assignment activity.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:manageactivities',
    ],
    'local_capstonebridge_create_url' => [
        'classname' => 'local_capstonebridge\external\create_url',
        'description' => 'Creates a URL resource in a course section.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:manageactivities,mod/url:addinstance',
    ],
    'local_capstonebridge_update_url' => [
        'classname' => 'local_capstonebridge\external\update_url',
        'description' => 'Updates the name, address, description, and section of a URL resource.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:manageactivities',
    ],
        'local_capstonebridge_create_quiz' => [
        'classname' => 'local_capstonebridge\external\create_quiz',
        'description' => 'Creates a Quiz with multiple choice questions from the course question bank.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:manageactivities,mod/quiz:addinstance,moodle/question:add',
    ],
    'local_capstonebridge_update_quiz' => [
        'classname' => 'local_capstonebridge\external\update_quiz',
        'description' => 'Updates a Quiz; questions are replaced only while it has no attempts.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:manageactivities,mod/quiz:manage,moodle/question:add',
    ],
        'local_capstonebridge_update_section' => [
        'classname' => 'local_capstonebridge\external\update_section',
        'description' => 'Updates the name and summary of a course section.',
        'type' => 'write',
        'ajax' => false,
        'capabilities' => 'moodle/course:update',
    ],
];
