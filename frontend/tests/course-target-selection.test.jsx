import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MoodleConnectionBanner from '../src/components/moodle/MoodleConnectionBanner';
import CourseTargetCard from '../src/components/ai/course/CourseTargetCard';
import CourseTargetSelectionPage from '../src/pages/dosen/ai/CourseTargetSelectionPage';

const moodleService = vi.hoisted(() => ({
  getMoodleStatus: vi.fn(),
  getMoodleCourses: vi.fn(),
  getMoodleCourse: vi.fn(),
  getMoodleCourseContents: vi.fn(),
}));

const workflowService = vi.hoisted(() => ({
  listWorkflows: vi.fn(),
  getWorkflow: vi.fn(),
  setWorkflowMoodleTarget: vi.fn(),
  getWorkflowEvents: vi.fn(),
}));

const rpsService = vi.hoisted(() => ({
  getRps: vi.fn(),
  listRps: vi.fn(),
}));

const courseContext = vi.hoisted(() => ({
  course: { id: 'course_001', workflow_id: 'workflow_001', moodle_course_id: '2', name: 'Pemrograman Web', code: 'IF2105', rps_id: 'rps_001' },
  refresh: vi.fn(),
}));

vi.mock('../src/services/moodleIntegrationService', () => moodleService);
vi.mock('../src/services/workflowService', () => workflowService);
vi.mock('../src/services/rpsService', () => rpsService);
vi.mock('../src/hooks/useCourse', () => ({ useCourse: () => courseContext }));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const SAMPLE_COURSES = [
  {
    id: 2,
    fullname: 'Pemrograman Web',
    shortname: 'IF2105',
    category: 'Teknik Informatika',
    summary: 'Pengembangan aplikasi web modern dengan HTML, CSS, dan JS.',
  },
  {
    id: 3,
    fullname: 'Basis Data',
    shortname: 'IF2203',
    category: 'Teknik Informatika',
    summary: 'Konsep basis data relasional, SQL, dan normalisasi.',
  },
  {
    id: 4,
    fullname: 'Pemrograman Web (Kelas B)',
    shortname: 'IF2105-B',
    category: 'Sistem Informasi',
    summary: 'Kelas paralel Pemrograman Web.',
  },
];

const SAMPLE_WORKFLOW = {
  id: 'workflow_001',
  status: 'COMPLETED',
  stage: 'FINAL_REVIEW',
  progress: { completed: 4, total: 4 },
  rps_id: 'rps_001',
  moodle_course_id: 2,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
};

let node;
let root;

beforeEach(() => {
  vi.resetAllMocks();
  courseContext.course = { id: 'course_001', workflow_id: 'workflow_001', moodle_course_id: '2', name: 'Pemrograman Web', code: 'IF2105', rps_id: 'rps_001' };
  courseContext.refresh.mockReset();

  moodleService.getMoodleStatus.mockResolvedValue({
    status: 'CONNECTED',
    connected: true,
    site_name: 'Moodle ITK',
    message: 'Terhubung ke Moodle LMS ITK.',
  });
  moodleService.getMoodleCourses.mockResolvedValue({
    courses: SAMPLE_COURSES,
  });
  moodleService.getMoodleCourseContents.mockResolvedValue({
    moodle_course_id: 3,
    sections: [
      { moodle_section_id: 30, section_number: 0, name: 'General', modules: [{ name: 'Pengumuman', modname: 'forum' }] },
      { moodle_section_id: 31, section_number: 1, name: 'Minggu 1: Konsep basis data', modules: [] },
    ],
  });
  workflowService.listWorkflows.mockResolvedValue({
    items: [SAMPLE_WORKFLOW],
  });
  workflowService.getWorkflow.mockResolvedValue(SAMPLE_WORKFLOW);
  workflowService.setWorkflowMoodleTarget.mockImplementation(async (id, moodleId) => {
    return { id, moodle_course_id: moodleId };
  });
  rpsService.getRps.mockResolvedValue({
    id: 'rps_001',
    filename: 'RPS_Pemrograman_Web.pdf',
    workflow_id: 'workflow_001',
  });

  node = document.createElement('div');
  document.body.appendChild(node);
});

afterEach(async () => {
  await act(async () => root?.unmount());
  root = null;
  node.remove();
});

async function renderComponent(component) {
  root ??= createRoot(node);
  await act(async () => root.render(component));
}

function typeInput(input, value) {
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

describe('FE-09.1 MoodleConnectionBanner', () => {
  it('renders loading indicator when loading and no status', async () => {
    await renderComponent(<MoodleConnectionBanner loading={true} />);
    expect(node.textContent).toContain('Memeriksa koneksi Moodle LMS');
  });

  it('renders connected state with site name and message', async () => {
    await renderComponent(
      <MoodleConnectionBanner
        status="CONNECTED"
        connected
        siteName="Moodle ITK"
        message="Terhubung ke Moodle LMS ITK."
      />
    );
    expect(node.textContent).toContain('Moodle LMS Terhubung');
    expect(node.textContent).toContain('Moodle ITK');
    expect(node.textContent).toContain('Terhubung ke Moodle LMS ITK.');
  });

  it('renders disconnected state with retry button and calls onRetry when clicked', async () => {
    const onRetry = vi.fn();
    await renderComponent(
      <MoodleConnectionBanner
        status="DISCONNECTED"
        message="Moodle unreachable"
        onRetry={onRetry}
      />
    );
    expect(node.textContent).toContain('Koneksi ke Moodle LMS Terputus');
    expect(node.textContent).toContain('Moodle unreachable');

    const retryBtn = node.querySelector('button');
    expect(retryBtn).not.toBeNull();
    expect(retryBtn.textContent).toContain('Coba Lagi');

    await act(async () => {
      retryBtn.click();
    });
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('renders error state gracefully when error object is provided', async () => {
    const error = new Error('Koneksi socket Moodle timeout.');
    await renderComponent(<MoodleConnectionBanner error={error} onRetry={vi.fn()} />);
    expect(node.textContent).toContain('Koneksi ke Moodle LMS Terputus');
    expect(node.textContent).toContain('Koneksi socket Moodle timeout.');
  });
});

describe('FE-09.1 CourseTargetCard', () => {
  const course = SAMPLE_COURSES[0];

  it('renders course details properly', async () => {
    await renderComponent(<CourseTargetCard course={course} isSelected={false} onSelect={vi.fn()} />);
    expect(node.textContent).toContain('Pemrograman Web');
    expect(node.textContent).toContain('IF2105');
    expect(node.textContent).toContain('ID: 2');
    expect(node.textContent).toContain('Teknik Informatika');
    expect(node.textContent).toContain('Pengembangan aplikasi web modern');
  });

  it('renders unselected state with action button and handles click', async () => {
    const onSelect = vi.fn();
    await renderComponent(<CourseTargetCard course={course} isSelected={false} onSelect={onSelect} />);

    const button = node.querySelector('button');
    expect(button.textContent).toContain('Pilih Course Target');

    await act(async () => {
      button.click();
    });
    expect(onSelect).toHaveBeenCalledWith(course);
  });

  it('renders selected state with active indicator and disabled button', async () => {
    await renderComponent(<CourseTargetCard course={course} isSelected={true} onSelect={vi.fn()} />);
    expect(node.textContent).toContain('Target Terpilih');
    const button = node.querySelector('button');
    expect(button.textContent).toContain('Terpilih');
    expect(button.disabled).toBe(true);
  });
});

describe('FE-09.2 CourseTargetSelectionPage (Workflow Integration & Modal Confirmation)', () => {
  it('loads status, courses, and marks saved target from GET /api/v1/workflows/{id}', async () => {
    await renderComponent(<CourseTargetSelectionPage />);

    expect(node.textContent).toContain('Pilih Target Course Moodle');
    expect(node.textContent).toContain('Moodle LMS Terhubung');
    expect(workflowService.getWorkflow).toHaveBeenCalledWith('workflow_001');
    expect(node.textContent).toContain('Target Terpilih');
  });

  it('filters courses by search query and resets search', async () => {
    await renderComponent(<CourseTargetSelectionPage />);

    const searchInput = node.querySelector('input[type="text"]');
    expect(searchInput).not.toBeNull();

    await act(async () => {
      typeInput(searchInput, 'Basis');
    });

    expect(node.textContent).toContain('Basis Data');
    expect(node.textContent).not.toContain('Pemrograman Web (Kelas B)');
    expect(node.textContent).toContain('Menampilkan 1 dari 3 kursus');

    await act(async () => {
      typeInput(searchInput, 'Kalkulus');
    });

    expect(node.textContent).toContain('Kursus tidak ditemukan');
    expect(node.textContent).toContain('Reset Pencarian');

    const resetBtn = Array.from(node.querySelectorAll('button')).find((b) =>
      b.textContent.includes('Reset Pencarian')
    );
    await act(async () => {
      resetBtn.click();
    });

    expect(node.textContent).toContain('Menampilkan 3 dari 3 kursus');
  });

  it('opens confirmation modal dialog when user clicks "Pilih Course Target"', async () => {
    await renderComponent(<CourseTargetSelectionPage />);

    const selectButtons = Array.from(node.querySelectorAll('button')).filter((b) =>
      b.textContent.includes('Pilih Course Target')
    );
    expect(selectButtons.length).toBeGreaterThan(0);

    await act(async () => {
      selectButtons[0].click();
    });

    expect(node.textContent).toContain('Konfirmasi Target Course Moodle');
    expect(node.textContent).toContain('Basis Data');
    expect(node.textContent).toContain('IF2203');
    expect(node.textContent).toContain('Konfirmasi & Simpan');
    expect(node.textContent).toContain('Batal');

    expect(workflowService.setWorkflowMoodleTarget).not.toHaveBeenCalled();
  });

  it('cancels confirmation modal when Batal is clicked without calling API', async () => {
    await renderComponent(<CourseTargetSelectionPage />);

    const selectButtons = Array.from(node.querySelectorAll('button')).filter((b) =>
      b.textContent.includes('Pilih Course Target')
    );
    await act(async () => {
      selectButtons[0].click();
    });

    expect(node.textContent).toContain('Konfirmasi Target Course Moodle');

    const cancelBtn = Array.from(node.querySelectorAll('dialog button, .btn--ghost')).find((b) =>
      b.textContent.trim() === 'Batal'
    );
    expect(cancelBtn).not.toBeNull();

    await act(async () => {
      cancelBtn.click();
    });

    expect(workflowService.setWorkflowMoodleTarget).not.toHaveBeenCalled();
  });

  it('calls setWorkflowMoodleTarget and persists target when Konfirmasi & Simpan is clicked', async () => {
    await renderComponent(<CourseTargetSelectionPage />);

    const selectButtons = Array.from(node.querySelectorAll('button')).filter((b) =>
      b.textContent.includes('Pilih Course Target')
    );
    await act(async () => {
      selectButtons[0].click();
    });

    const confirmBtn = Array.from(node.querySelectorAll('button')).find((b) =>
      b.textContent.includes('Konfirmasi & Simpan')
    );
    expect(confirmBtn).not.toBeNull();

    await act(async () => {
      confirmBtn.click();
    });

    expect(workflowService.setWorkflowMoodleTarget).toHaveBeenCalledWith('workflow_001', 3);
    expect(node.textContent).toContain('berhasil disimpan sebagai target Moodle');
  });

  it('displays warning and disables course target selection when workflow is not active', async () => {
    courseContext.course = { id: 'course_002', workflow_id: null, rps_id: null, name: 'Kalkulus' };
    workflowService.listWorkflows.mockResolvedValue({ items: [] });
    await renderComponent(<CourseTargetSelectionPage />);

    expect(node.textContent).toContain('Dokumen RPS belum selesai dianalisis');

    const selectButtons = Array.from(node.querySelectorAll('button')).filter((b) =>
      b.textContent.includes('Pilih Course Target')
    );
    expect(selectButtons.every((b) => b.disabled)).toBe(true);
  });

  it('handles empty courses list from Moodle', async () => {
    moodleService.getMoodleCourses.mockResolvedValue({ courses: [] });

    await renderComponent(<CourseTargetSelectionPage />);

    expect(node.textContent).toContain('Tidak ada kursus Moodle ditemukan');
  });

  it('handles Moodle connection error gracefully without crashing', async () => {
    moodleService.getMoodleStatus.mockRejectedValue(new Error('Gagal terhubung ke host Moodle'));
    moodleService.getMoodleCourses.mockRejectedValue(new Error('Koneksi Moodle terputus'));

    await renderComponent(<CourseTargetSelectionPage />);

    expect(node.textContent).toContain('Koneksi ke Moodle LMS Terputus');
    expect(node.textContent).toContain('Gagal terhubung ke host Moodle');
    // Gagal memuat bukan berarti kosong: tanpa keadaan "tidak ada kursus" dan tanpa pesan ganda.
    expect(node.textContent).not.toContain('Tidak ada kursus Moodle ditemukan');
    expect(node.textContent).not.toContain('Koneksi Moodle terputus');
    expect(node.querySelector('input[type="text"]')).toBeNull();
  });

  it('shows the course list error once when only the course list fails', async () => {
    moodleService.getMoodleCourses.mockRejectedValue(new Error('Daftar kursus belum dapat dimuat.'));

    await renderComponent(<CourseTargetSelectionPage />);

    expect(node.textContent).toContain('Moodle LMS Terhubung');
    expect(node.textContent.match(/Daftar kursus belum dapat dimuat\./g)).toHaveLength(1);
    expect(node.textContent).not.toContain('Tidak ada kursus Moodle ditemukan');
  });

  it('menampilkan target saat ini dari daftar kursus', async () => {
    await renderComponent(<CourseTargetSelectionPage />);
    expect(node.querySelector('[aria-label="Target saat ini"]').textContent).toContain('Pemrograman Web (IF2105)');
    expect(moodleService.getMoodleCourse).not.toHaveBeenCalled();
  });

  it('target yang tidak ada di daftar diambil dari GET /integrations/moodle/courses/{id}', async () => {
    workflowService.getWorkflow.mockResolvedValue({ ...SAMPLE_WORKFLOW, moodle_course_id: 99 });
    moodleService.getMoodleCourse.mockResolvedValue({ id: 99, fullname: 'Kursus Arsip', shortname: 'ARS-1' });
    await renderComponent(<CourseTargetSelectionPage />);
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    expect(moodleService.getMoodleCourse).toHaveBeenCalledWith('99');
    expect(node.querySelector('[aria-label="Target saat ini"]').textContent).toContain('Kursus Arsip (ARS-1)');
  });

  it('dialog konfirmasi menampilkan pratinjau isi kursus Moodle yang dipilih', async () => {
    await renderComponent(<CourseTargetSelectionPage />);
    const selectButtons = Array.from(node.querySelectorAll('button')).filter((b) => b.textContent.includes('Pilih Course Target'));
    await act(async () => selectButtons[0].click());
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    expect(moodleService.getMoodleCourseContents).toHaveBeenCalledWith(3);
    const preview = node.querySelector('[aria-label="Isi kursus Moodle saat ini"]');
    expect(preview.textContent).toContain('General · 1 aktivitas');
    expect(preview.textContent).toContain('Minggu 1: Konsep basis data · 0 aktivitas');
  });

  it('pratinjau yang gagal dimuat tidak menghalangi konfirmasi', async () => {
    moodleService.getMoodleCourseContents.mockRejectedValue(new Error('Layanan sedang tidak dapat diakses.'));
    await renderComponent(<CourseTargetSelectionPage />);
    const selectButtons = Array.from(node.querySelectorAll('button')).filter((b) => b.textContent.includes('Pilih Course Target'));
    await act(async () => selectButtons[0].click());
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
    expect(node.querySelector('[aria-label="Isi kursus Moodle saat ini"]').textContent).toContain('Isi kursus belum dapat dimuat.');
    expect(Array.from(node.querySelectorAll('button')).find((b) => b.textContent.includes('Konfirmasi & Simpan')).disabled).toBe(false);
  });
});
