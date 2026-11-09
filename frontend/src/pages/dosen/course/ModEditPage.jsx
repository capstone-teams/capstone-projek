import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useCourseBreadcrumb, useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useCourseEditing } from '../../../hooks/useCourseEditing';
import { CAN_CREATE_IN_APP } from '../../../services/moodle/courseEditing';
import { EmptyState } from '../../../components/ui';
import ActivityIcon from '../../../components/moodle/ActivityIcon';
import { AssignModForm, LabelModForm, QuizModForm } from '../../../components/moodle/modedit/ModForms';

const TYPES = {
  assign: { name: 'Assignment', Form: AssignModForm, successMessage: 'Tugas ditambahkan.' },
  quiz: { name: 'Quiz', Form: QuizModForm, successMessage: 'Kuis ditambahkan.' },
  label: { name: 'Text and media area', Form: LabelModForm, successMessage: 'Teks dan media ditambahkan.' },
};

/** Halaman "New <aktivitas>". Rujukan alur Moodle: course/modedit.php?add=<modname>&section=<n>. */
export default function ModEditPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { course, sections, canEdit } = useMoodleCourse();
  const editing = useCourseEditing();
  const [error, setError] = useState(null);
  const modname = params.get('add');
  const type = TYPES[modname];
  const section = sections.find((s) => s.section === Number(params.get('section')));
  const coursePath = `/course/${course.id}`;
  useCourseBreadcrumb(type && section ? [{ label: section.name, to: `${coursePath}#section-${section.section}` }, { label: `New ${type.name}` }] : []);

  if (!canEdit) {
    return <EmptyState title="Anda tidak dapat menambah aktivitas di kursus ini." action={<Link to={coursePath}>Kembali ke kursus</Link>} />;
  }
  if (!type || !section) {
    return <EmptyState title="Jenis aktivitas atau section tidak ditemukan." action={<Link to={coursePath}>Kembali ke kursus</Link>} />;
  }

  const sectionPath = `${coursePath}#section-${section.section}`;
  // Argumen kedua dari formulir (prompt tambahan dan pilihan generate) sengaja tidak dipakai: backend belum punya
  // endpoint generate konten aktivitas, dan prompt tidak boleh ikut terkirim sebagai isian aktivitas. Begitu
  // endpoint tersedia, berikan `onGenerate` ke formulir agar tombol "Generate dengan AI" aktif.
  const submit = async (fields) => {
    setError(null);
    const result = await editing.createActivity(section, modname, fields, type.successMessage, setError);
    // Simpan selalu kembali ke section tempat aktivitas ditambahkan.
    if (result) navigate(sectionPath);
  };

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <ActivityIcon modname={modname} />
        <h2 className="text-2xl">New {type.name}</h2>
      </div>
      <type.Form
        key={`${modname}-${section.id}`}
        canCreate={CAN_CREATE_IN_APP}
        pending={editing.pending === `create:${section.id}`}
        error={error}
        onSubmit={submit}
        onCancel={() => navigate(sectionPath)}
      />
    </div>
  );
}
