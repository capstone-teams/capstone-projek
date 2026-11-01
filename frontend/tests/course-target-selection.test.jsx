import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MoodleConnectionBanner from '../src/components/moodle/MoodleConnectionBanner';
import CourseTargetCard from '../src/components/ai/course/CourseTargetCard';
import CourseTargetSelectionPage from '../src/pages/dosen/ai/CourseTargetSelectionPage';

// Mock service dan hook useCourse
const moodleService = vi.hoisted(() => ({
  getMoodleStatus: vi.fn(),
  getMoodleCourses: vi.fn(),
}));

const courseContext = vi.hoisted(() => ({
  course: { id: 'course_001', moodle_course_id: '2', name: 'Pemrograman Web', code: 'IF2105' },
  refresh: vi.fn(),
}));

vi.mock('../src/services/moodleIntegrationService', () => moodleService);
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

let node;
let root;

beforeEach(() => {
  vi.resetAllMocks();
  courseContext.course = { id: 'course_001', moodle_course_id: '2', name: 'Pemrograman Web', code: 'IF2105' };
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

  it('renders connected state with Moodle URL and message', async () => {
    await renderComponent(
      <MoodleConnectionBanner
        status="CONNECTED"
        moodleUrl="http://localhost:8080"
        message="Terhubung ke Moodle LMS ITK."
      />
    );
    expect(node.textContent).toContain('Moodle LMS Terhubung');
    expect(node.textContent).toContain('http://localhost:8080');
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

describe('FE-09.1 CourseTargetSelectionPage', () => {
  it('loads status and courses list and renders them into the grid', async () => {
    moodleService.getMoodleStatus.mockResolvedValue({
      status: 'CONNECTED',
      moodle_url: 'http://localhost:8080',
      message: 'Terhubung ke Moodle LMS ITK.',
    });
    moodleService.getMoodleCourses.mockResolvedValue({
      courses: SAMPLE_COURSES,
    });

    await renderComponent(<CourseTargetSelectionPage />);

    expect(node.textContent).toContain('Pilih Target Course Moodle');
    expect(node.textContent).toContain('Moodle LMS Terhubung');
    expect(node.textContent).toContain('Pemrograman Web');
    expect(node.textContent).toContain('Basis Data');
    expect(node.textContent).toContain('Pemrograman Web (Kelas B)');
    expect(node.textContent).toContain('Menampilkan 3 dari 3 kursus');
  });

  it('filters courses by search query and resets search', async () => {
    moodleService.getMoodleStatus.mockResolvedValue({ status: 'CONNECTED', moodle_url: 'http://localhost:8080' });
    moodleService.getMoodleCourses.mockResolvedValue({ courses: SAMPLE_COURSES });

    await renderComponent(<CourseTargetSelectionPage />);

    const searchInput = node.querySelector('input[type="text"]');
    expect(searchInput).not.toBeNull();

    // Cari "Basis"
    await act(async () => {
      typeInput(searchInput, 'Basis');
    });

    expect(node.textContent).toContain('Basis Data');
    expect(node.textContent).not.toContain('Pemrograman Web (Kelas B)');
    expect(node.textContent).toContain('Menampilkan 1 dari 3 kursus');

    // Cari string yang tidak ada
    await act(async () => {
      typeInput(searchInput, 'Kalkulus');
    });

    expect(node.textContent).toContain('Kursus tidak ditemukan');
    expect(node.textContent).toContain('Reset Pencarian');

    // Klik tombol reset pencarian
    const resetBtn = Array.from(node.querySelectorAll('button')).find((b) =>
      b.textContent.includes('Reset Pencarian')
    );
    await act(async () => {
      resetBtn.click();
    });

    expect(node.textContent).toContain('Menampilkan 3 dari 3 kursus');
  });

  it('allows user to select a course target and updates selected status and feedback message', async () => {
    moodleService.getMoodleStatus.mockResolvedValue({ status: 'CONNECTED', moodle_url: 'http://localhost:8080' });
    moodleService.getMoodleCourses.mockResolvedValue({ courses: SAMPLE_COURSES });

    await renderComponent(<CourseTargetSelectionPage />);

    // Awalnya course ID 2 adalah terpilih dari context
    expect(node.textContent).toContain('Target Terpilih');

    // Cari tombol "Pilih Course Target" untuk Basis Data (ID: 3)
    const selectButtons = Array.from(node.querySelectorAll('button')).filter((b) =>
      b.textContent.includes('Pilih Course Target')
    );
    expect(selectButtons.length).toBeGreaterThan(0);

    await act(async () => {
      selectButtons[0].click();
    });

    // Cek pesan sukses dan status terpilih berpindah
    expect(node.textContent).toContain('dipilih sebagai target sinkronisasi Moodle');
  });

  it('handles empty courses list from Moodle', async () => {
    moodleService.getMoodleStatus.mockResolvedValue({ status: 'CONNECTED', moodle_url: 'http://localhost:8080' });
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
    expect(node.textContent).toContain('Koneksi Moodle terputus');
  });
});
