import { useState } from 'react';
import { Modal } from '../../ui';
import ActivityChooser from './ActivityChooser';
import { AssignmentForm, QuizForm } from './DatedActivityForm';
import TextMediaForm from './TextMediaForm';
import { CAN_CREATE_IN_APP, moodleEditUrl } from '../../../services/moodle/courseEditing';

// Jenis aktivitas di pemilih. Warna ikon dan teks mengikuti dialog "Add an activity or resource" Moodle.
// `recommended` di Moodle diatur admin situs; di sini ditetapkan tetap.
const ACTIVITY_TYPES = [
  {
    modname: 'assign',
    name: 'Assignment',
    kind: 'activity',
    recommended: true,
    iconClass: 'bg-[#ee71ab]',
    description: 'Teachers can set tasks, collect students\' work and give grades and feedback.',
    Form: AssignmentForm,
    successMessage: 'Tugas ditambahkan.',
  },
  {
    modname: 'quiz',
    name: 'Quiz',
    kind: 'activity',
    recommended: true,
    iconClass: 'bg-[#ee71ab]',
    description: 'Teachers can create quizzes that students attempt and that are graded automatically.',
    Form: QuizForm,
    successMessage: 'Kuis ditambahkan.',
  },
  {
    modname: 'label',
    name: 'Text and media area',
    kind: 'resource',
    recommended: true,
    iconClass: 'bg-[#40a6e7]',
    description: 'Add text, images or video that appear directly on the course page.',
    Form: TextMediaForm,
    successMessage: 'Teks dan media ditambahkan.',
  },
];

/** Tambah aktivitas ke section: pilih jenis di pemilih, lalu isi formulirnya. */
export default function AddActivityModal({ open, courseId, section, editing, onClose }) {
  const [type, setType] = useState(null);
  const [error, setError] = useState(null);

  const submit = async (fields) => {
    setError(null);
    const ok = await editing.createActivity(section, type.modname, fields, type.successMessage, setError);
    if (ok) onClose();
  };

  return (
    <Modal open={open} title={type ? `Add a new ${type.name} to ${section.name}` : 'Add an activity or resource'} onClose={onClose} wide={!type}>
      {type ? (
        <type.Form
          canCreate={CAN_CREATE_IN_APP}
          moodleHref={moodleEditUrl.addActivity(courseId, section.section, type.modname)}
          pending={editing.pending === `create:${section.id}`}
          error={error}
          onSubmit={submit}
          onBack={() => { setType(null); setError(null); }}
        />
      ) : (
        <ActivityChooser types={ACTIVITY_TYPES} onChoose={setType} />
      )}
    </Modal>
  );
}
