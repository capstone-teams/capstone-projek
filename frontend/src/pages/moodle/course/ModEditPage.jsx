import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useCourseEditing } from '../../../hooks/useCourseEditing';
import { CAN_CREATE_IN_APP, moodleEditUrl } from '../../../services/moodle/courseEditing';
import { EmptyState } from '../../../components/ui';
import ActivityIcon from '../../../components/moodle/ActivityIcon';
import { AssignModForm, LabelModForm, QuizModForm } from '../../../components/moodle/modedit/ModForms';

const TYPES = {
  assign: { name: 'Assignment', Form: AssignModForm, successMessage: 'Tugas ditambahkan.' },
  quiz: { name: 'Quiz', Form: QuizModForm, successMessage: 'Kuis ditambahkan.' },
  label: { name: 'Text and media area', Form: LabelModForm, successMessage: 'Teks dan media ditambahkan.' },
};

/** Halaman "New <aktivitas>" (Moodle: course/modedit.php?add=<modname>&section=<n>). */
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

  if (!canEdit) {
    return <EmptyState title="Anda tidak dapat menambah aktivitas di kursus ini." action={<Link to={coursePath}>Kembali ke kursus</Link>} />;
  }
  if (!type || !section) {
    return <EmptyState title="Jenis aktivitas atau section tidak ditemukan." action={<Link to={coursePath}>Kembali ke kursus</Link>} />;
  }

  const sectionPath = `${coursePath}#section-${section.section}`;
  const submit = async (fields, display) => {
    setError(null);
    const result = await editing.createActivity(section, modname, fields, type.successMessage, setError);
    if (!result) return;
    // Save and display membuka aktivitas baru; Save and return to course kembali ke section-nya.
    navigate(display && result.cmid ? `${coursePath}/mod/${result.cmid}` : sectionPath);
  };

  return (
    <div>
      <nav className="mb-3 text-sm text-muted" aria-label="Breadcrumb aktivitas">
        <Link to={sectionPath}>{section.name}</Link>
        {' / '}
        <span aria-current="page">New {type.name}</span>
      </nav>
      <div className="mb-4 flex items-center gap-3">
        <ActivityIcon modname={modname} />
        <h2 className="text-2xl">New {type.name}</h2>
      </div>
      <type.Form
        key={`${modname}-${section.id}`}
        canCreate={CAN_CREATE_IN_APP}
        moodleHref={moodleEditUrl.addActivity(course.id, section.section, modname)}
        pending={editing.pending === `create:${section.id}`}
        error={error}
        onSubmit={submit}
        onCancel={() => navigate(sectionPath)}
      />
    </div>
  );
}
