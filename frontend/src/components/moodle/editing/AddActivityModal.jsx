import { useState } from 'react';
import { Modal } from '../../ui';
import ActivityIcon from '../ActivityIcon';
import AssignmentForm from './AssignmentForm';
import TextMediaForm from './TextMediaForm';
import { CAN_CREATE_IN_APP, moodleEditUrl } from '../../../services/moodle/courseEditing';

// Jenis yang ditampilkan di pemilih. Tahap ini baru Tugas dan Teks dan media; jenis lain
// cukup ditambahkan ke daftar ini beserta formulirnya.
const ACTIVITY_TYPES = [
  {
    modname: 'assign',
    label: 'Tugas',
    description: 'Mahasiswa mengunggah atau menulis jawaban untuk dinilai.',
    Form: AssignmentForm,
    successMessage: 'Tugas ditambahkan.',
  },
  {
    modname: 'label',
    label: 'Teks dan media',
    description: 'Teks, gambar, atau video yang tampil langsung di halaman kursus.',
    Form: TextMediaForm,
    successMessage: 'Teks dan media ditambahkan.',
  },
];

function TypeChooser({ onChoose }) {
  return (
    <ul className="grid grid-cols-2 gap-3" aria-label="Jenis aktivitas">
      {ACTIVITY_TYPES.map((type) => (
        <li key={type.modname}>
          <button
            type="button"
            className="flex h-full w-full cursor-pointer flex-col items-center gap-2 rounded-lg border border-line bg-white p-4 text-center text-ink transition-colors hover:border-primary hover:bg-primary-light focus-visible:outline-2 focus-visible:outline-primary"
            onClick={() => onChoose(type)}
          >
            <ActivityIcon modname={type.modname} src={`/moodle/mod/${type.modname}.svg`} />
            <span className="font-semibold">{type.label}</span>
            <span className="text-xs text-muted">{type.description}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Tambah aktivitas ke section: pilih jenis, lalu isi formulirnya di aplikasi. */
export default function AddActivityModal({ open, courseId, section, editing, onClose }) {
  const [type, setType] = useState(null);
  const [error, setError] = useState(null);

  const submit = async (fields) => {
    setError(null);
    const ok = await editing.createActivity(section, type.modname, fields, type.successMessage, setError);
    if (ok) onClose();
  };

  const title = type ? `Tambah ${type.label} ke "${section.name}"` : `Tambah aktivitas atau sumber ke "${section.name}"`;
  return (
    <Modal open={open} title={title} onClose={onClose}>
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
        <TypeChooser onChoose={setType} />
      )}
    </Modal>
  );
}
