import { useNavigate } from 'react-router-dom';
import { Modal } from '../../ui';
import ActivityChooser from './ActivityChooser';

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
  },
  {
    modname: 'quiz',
    name: 'Quiz',
    kind: 'activity',
    recommended: true,
    iconClass: 'bg-[#ee71ab]',
    description: 'Teachers can create quizzes that students attempt and that are graded automatically.',
  },
  {
    modname: 'label',
    name: 'Text and media area',
    kind: 'resource',
    recommended: true,
    iconClass: 'bg-[#40a6e7]',
    description: 'Add text, images or video that appear directly on the course page.',
  },
];

/**
 * Tambah aktivitas ke section: pilih jenis di pemilih, lalu buka halaman "New <aktivitas>"
 * seperti Moodle (course/modedit.php?add=<modname>&section=<n>).
 */
export default function AddActivityModal({ open, courseId, section, onClose }) {
  const navigate = useNavigate();
  const choose = (type) => {
    onClose();
    navigate(`/course/${courseId}/modedit?add=${type.modname}&section=${section.section}`);
  };

  return (
    <Modal open={open} title="Add an activity or resource" onClose={onClose} wide>
      <ActivityChooser types={ACTIVITY_TYPES} onChoose={choose} />
    </Modal>
  );
}
