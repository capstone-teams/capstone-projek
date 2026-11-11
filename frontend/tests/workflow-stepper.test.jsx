import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import WorkflowStepper from '../src/components/ai/WorkflowStepper';
import AiCourseLayout from '../src/pages/dosen/ai/AiCourseLayout';
import CourseOverviewPage from '../src/pages/dosen/ai/CourseOverviewPage';
import MyCoursesPage from '../src/pages/moodle/MyCoursesPage';
import ProfilePage from '../src/pages/moodle/ProfilePage';
import { AuthContext } from '../src/context/authContext';
import { AppStateProvider } from '../src/context/AppStateProvider';
import * as courseService from '../src/services/courseService';
import * as coursePlanService from '../src/services/coursePlanService';
import * as contentService from '../src/services/contentService';
import * as executionService from '../src/services/executionService';
import * as workflowService from '../src/services/workflowService';
import * as rpsService from '../src/services/rpsService';
import * as moodleApi from '../src/services/moodle/moodleApi';
import { ROLE } from '../src/types/auth';
import { deriveStepperState } from '../src/utils/workflowStatus';

const moodleCourseHook = vi.hoisted(() => ({
  course: { id: 48, shortname: 'SBD-2223', fullname: 'Sistem Basis Data' },
  isTeacher: true,
}));
const monitorState = vi.hoisted(() => ({
  workflow: null,
  events: [],
  connection: 'connected',
  reload: vi.fn(),
}));

vi.mock('../src/hooks/useMoodleCourse', () => ({ useMoodleCourse: () => moodleCourseHook }));
vi.mock('../src/hooks/useWorkflowMonitor', () => ({ useWorkflowMonitor: () => monitorState }));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const ev = (event, stage = null, message = '') => ({
  event,
  stage,
  message,
  workflow_id: 'wf-1',
  timestamp: '2026-11-11T08:00:00Z',
});
const wf = (overrides = {}) => ({
  id: 'wf-1',
  rps_id: 'rps-1',
  moodle_course_id: 48,
  status: 'RUNNING',
  stage: 'instructor_review',
  updated_at: '2026-11-11T08:00:00Z',
  ...overrides,
});

const analyzed = () => [
  ev('WORKFLOW_STAGE_STARTED', 'rps_analysis'),
  ev('WORKFLOW_STAGE_COMPLETED', 'rps_analysis'),
  ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review'),
];
const planned = () => [
  ...analyzed(),
  ev('WORKFLOW_STAGE_STARTED', 'course_planning'),
  ev('WORKFLOW_STAGE_COMPLETED', 'course_planning'),
  ev('WORKFLOW_STAGE_STARTED', 'validation'),
  ev('WORKFLOW_PLAN_GENERATED', 'validation'),
  ev('WORKFLOW_STAGE_COMPLETED', 'validation'),
  ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review'),
];
const approved = () => [...planned(), ev('WORKFLOW_PLAN_APPROVED', 'instructor_review')];
const contentGen = () => [
  ...approved(),
  ev('WORKFLOW_STAGE_STARTED', 'content_generation'),
];
const contentReview = () => [
  ...contentGen(),
  ev('WORKFLOW_STAGE_COMPLETED', 'content_generation'),
  ev('WORKFLOW_STAGE_STARTED', 'validation'),
  ev('WORKFLOW_CONTENT_VALIDATED', 'validation', 'Minggu 1 - Learning Material selesai.'),
  ev('WORKFLOW_STAGE_COMPLETED', 'validation'),
  ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review'),
];
const contentApproved = () => [...contentReview(), ev('WORKFLOW_CONTENTS_APPROVED', 'instructor_review')];
const fullExecuted = () => [
  ...contentApproved(),
  ev('WORKFLOW_STAGE_STARTED', 'moodle_execution'),
  ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution', 'Minggu 1 - Quiz diterapkan ke Moodle.'),
  ev('WORKFLOW_STAGE_COMPLETED', 'moodle_execution'),
  ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review'),
];

describe('WorkflowStepper & deriveStepperState (data workflow backend)', () => {
  it('memetakan seluruh tahapan workflow nyata dari Rencana hingga Selesai', () => {
    expect(deriveStepperState(null, [])).toEqual({ current: 0, finished: false });
    expect(deriveStepperState(wf({ stage: 'rps_analysis' }), [])).toEqual({ current: 0, finished: false });
    expect(deriveStepperState(wf(), planned())).toEqual({ current: 0, finished: false });
    expect(deriveStepperState(wf(), approved())).toEqual({ current: 1, finished: false });
    expect(deriveStepperState(wf({ stage: 'content_generation' }), contentGen())).toEqual({ current: 1, finished: false });
    expect(deriveStepperState(wf({ stage: 'validation' }), contentGen())).toEqual({ current: 1, finished: false });
    expect(deriveStepperState(wf(), contentReview())).toEqual({ current: 2, finished: false });
    expect(deriveStepperState(wf(), contentApproved())).toEqual({ current: 3, finished: false });
    expect(deriveStepperState(wf({ stage: 'moodle_execution' }), contentApproved())).toEqual({ current: 3, finished: false });
    expect(deriveStepperState(wf(), fullExecuted())).toEqual({ current: 4, finished: false });
    expect(deriveStepperState(wf({ status: 'COMPLETED', stage: null }), fullExecuted())).toEqual({ current: 5, finished: true });
  });

  it('tidak mundur ke Konten saat sebagian konten sudah disetujui, diregenerasi, atau pasca-eksekusi struktur', () => {
    const partialContents = [
      { id: 'c1', status: 'APPROVED' },
      { id: 'c2', status: 'DRAFT' },
    ];
    const allApprovedContents = [
      { id: 'c1', status: 'APPROVED' },
      { id: 'c2', status: 'APPROVED' },
    ];
    const structureAfterReviewEvents = [
      ...contentApproved(),
      ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution', 'Minggu 1 diterapkan ke Moodle.'),
      ev('WORKFLOW_STAGE_COMPLETED', 'moodle_execution'),
      ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review'),
    ];

    // 4/8 disetujui -> tetap di langkah (3) Review (index 2), belum lompat ke Eksekusi Moodle
    expect(deriveStepperState(wf(), contentApproved(), {
      plan: { status: 'APPROVED' },
      contents: partialContents,
    })).toEqual({ current: 2, finished: false });

    // Setelah eksekusi STRUCTURE berjalan belakangan -> tetap tidak turun kembali ke Konten
    expect(deriveStepperState(wf(), structureAfterReviewEvents, {
      plan: { status: 'APPROVED' },
      contents: partialContents,
      executions: [{ scope: 'STRUCTURE', status: 'SUCCESS' }],
    })).toEqual({ current: 2, finished: false });
    expect(deriveStepperState(wf(), structureAfterReviewEvents)).toEqual({ current: 2, finished: false });

    // Sedang regenerasi item ketika daftar konten sudah ada -> progres tetap tidak mundur
    expect(deriveStepperState(wf({ stage: 'content_generation' }), contentGen(), {
      plan: { status: 'APPROVED' },
      contents: partialContents,
    })).toEqual({ current: 2, finished: false });

    // 8/8 disetujui -> maju ke langkah (4) Eksekusi Moodle (index 3)
    expect(deriveStepperState(wf(), structureAfterReviewEvents, {
      plan: { status: 'APPROVED' },
      contents: allApprovedContents,
      executions: [{ scope: 'STRUCTURE', status: 'SUCCESS' }],
    })).toEqual({ current: 3, finished: false });
  });

  it('menandai langkah yang selesai dengan ✓ pada komponen WorkflowStepper', async () => {
    const node = document.createElement('div');
    const root = createRoot(node);
    await act(async () => root.render(<WorkflowStepper workflow={wf()} events={contentReview()} />));
    const items = [...node.querySelectorAll('.stepper__item')];
    expect(items[0].className).toContain('stepper__item--done');
    expect(items[1].className).toContain('stepper__item--done');
    expect(items[2].className).toContain('stepper__item--current');
    expect(items[2].getAttribute('aria-current')).toBe('step');
    expect(items[3].className).toContain('stepper__item--todo');
    await act(async () => root.unmount());
  });
});

describe('AiCourseLayout & CourseOverviewPage tanpa fallback mock DRAFT', () => {
  let node;
  let root;

  beforeEach(() => {
    vi.restoreAllMocks();
    node = document.createElement('div');
    document.body.appendChild(node);
    root = createRoot(node);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    node.remove();
  });

  it('AiCourseLayout menampilkan status workflow nyata & stepper maju saat rencana disetujui', async () => {
    vi.spyOn(courseService, 'findCourseByMoodleId').mockResolvedValue(null);
    vi.spyOn(workflowService, 'getActiveCourseBinding').mockReturnValue({ workflowId: 'wf-1', rpsId: 'rps-1' });
    vi.spyOn(workflowService, 'findWorkflowForCourse').mockResolvedValue(wf());
    vi.spyOn(rpsService, 'getRps').mockResolvedValue({ id: 'rps-1', filename: 'RPS SBD.pdf', status: 'ANALYZED' });

    monitorState.workflow = wf();
    monitorState.events = approved();

    await act(async () => root.render(
      <MemoryRouter initialEntries={['/course/48/ai']}>
        <Routes>
          <Route path="/course/:courseId/ai" element={<AiCourseLayout />}>
            <Route index element={<CourseOverviewPage />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    ));

    // Tidak lagi menampakkan badge Draft hardcoded
    expect(node.textContent).toContain('Menunggu review Anda');
    expect(node.textContent).not.toMatch(/\bDraft\b/);

    // Step 1 (Rencana) done (✓), Step 2 (Konten) current
    const items = [...node.querySelectorAll('.stepper__item')];
    expect(items[0].className).toContain('stepper__item--done');
    expect(items[1].className).toContain('stepper__item--current');

    // Overview menampilkan langkah berikutnya dan timeline event nyata
    expect(node.textContent).toContain('Eksekusi struktur');
    expect(node.textContent).toContain('RPS SBD.pdf');
  });

  it('AiCourseLayout menjaga stepper di Review saat konten sudah ada & sebagian disetujui', async () => {
    vi.spyOn(courseService, 'findCourseByMoodleId').mockResolvedValue(null);
    vi.spyOn(workflowService, 'getActiveCourseBinding').mockReturnValue({ workflowId: 'wf-1', rpsId: 'rps-1' });
    vi.spyOn(workflowService, 'findWorkflowForCourse').mockResolvedValue(wf());
    vi.spyOn(rpsService, 'getRps').mockResolvedValue({ id: 'rps-1', filename: 'RPS SBD.pdf', status: 'ANALYZED' });
    vi.spyOn(coursePlanService, 'getWorkflowPlan').mockResolvedValue({ id: 'plan-1', status: 'APPROVED' });
    vi.spyOn(contentService, 'listWorkflowContents').mockResolvedValue([
      { id: 'c1', status: 'APPROVED' },
      { id: 'c2', status: 'FAILED' },
    ]);
    vi.spyOn(executionService, 'listExecutions').mockResolvedValue([{ execution_id: 'ex-1', scope: 'STRUCTURE', status: 'SUCCESS' }]);

    monitorState.workflow = wf();
    monitorState.events = [
      ...contentApproved(),
      ev('WORKFLOW_MOODLE_OPERATION', 'moodle_execution', 'Minggu 1 diterapkan ke Moodle.'),
      ev('WORKFLOW_STAGE_COMPLETED', 'moodle_execution'),
      ev('WORKFLOW_WAITING_FOR_REVIEW', 'instructor_review'),
    ];

    await act(async () => root.render(
      <MemoryRouter initialEntries={['/course/48/ai']}>
        <Routes>
          <Route path="/course/:courseId/ai" element={<AiCourseLayout />}>
            <Route index element={<CourseOverviewPage />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    ));

    const items = [...node.querySelectorAll('.stepper__item')];
    expect(items[0].className).toContain('stepper__item--done');
    expect(items[1].className).toContain('stepper__item--done');
    expect(items[2].className).toContain('stepper__item--current');
    expect(items[3].className).toContain('stepper__item--todo');
    expect(node.textContent).toContain('Review konten');
  });

  it('Mahasiswa (STUDENT) menerima kursus terdaftarnya tanpa error 403 /courses fallback atau ProfilePage error', async () => {
    const gatewaySpy = vi.spyOn(moodleApi, 'getCoursesByClassification').mockResolvedValue([
      { id: 48, shortname: 'SBD-2223', fullname: 'Sistem Basis Data' },
    ]);
    const studentAuth = {
      user: {
        id: 'u-stu-1',
        username: '11231023',
        fullname: 'Mahasiswa Demo',
        email: '11231023@student.itk.ac.id',
        role: ROLE.MAHASISWA,
        isAdmin: false,
      },
      site: { name: 'Moodle ITK' },
    };

    await act(async () => root.render(
      <MemoryRouter>
        <AuthContext.Provider value={studentAuth}>
          <AppStateProvider>
            <MyCoursesPage />
            <ProfilePage />
          </AppStateProvider>
        </AuthContext.Provider>
      </MemoryRouter>,
    ));

    expect(gatewaySpy).toHaveBeenCalled();
    expect(node.textContent).toContain('Mahasiswa Demo');
    expect(node.textContent).toContain('11231023@student.itk.ac.id');
    expect(node.textContent).toContain('Sistem Basis Data');
  });

  it('AiCourseLayout otomatis menyinkronkan moodle_course_id setelah proses background selesai tanpa banner manual', async () => {
    vi.spyOn(courseService, 'findCourseByMoodleId').mockResolvedValue(null);
    vi.spyOn(workflowService, 'getActiveCourseBinding').mockReturnValue({
      workflowId: 'wf-1',
      rpsId: 'rps-1',
      pendingTargetSync: true,
    });
    vi.spyOn(workflowService, 'findWorkflowForCourse').mockResolvedValue(wf({ moodle_course_id: null }));
    const bindSpy = vi.spyOn(workflowService, 'bindWorkflowToCourse').mockResolvedValue(wf({ moodle_course_id: 48 }));
    vi.spyOn(rpsService, 'getRps').mockResolvedValue({ id: 'rps-1', filename: 'RPS SBD.pdf', status: 'ANALYZED' });

    const tree = () => (
      <MemoryRouter initialEntries={['/course/48/ai']}>
        <Routes>
          <Route path="/course/:courseId/ai" element={<AiCourseLayout />}>
            <Route index element={<CourseOverviewPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    // Saat analisis masih berjalan (busy), sinkronisasi menunggu tenang dan tidak memunculkan banner manual
    monitorState.workflow = wf({ status: 'RUNNING', stage: 'rps_analysis', moodle_course_id: 48 });
    monitorState.events = [ev('WORKFLOW_STAGE_STARTED', 'rps_analysis')];
    await act(async () => root.render(tree()));
    expect(bindSpy).not.toHaveBeenCalled();
    expect(node.textContent).not.toContain('RPS belum tersimpan untuk kursus ini');
    expect(node.textContent).not.toContain('Simpan sebagai RPS kursus');

    // Setelah selesai analisis ke WAITING_FOR_REVIEW (tidak busy), target kursus otomatis diikat ulang
    monitorState.workflow = wf({
      status: 'RUNNING',
      stage: 'instructor_review',
      moodle_course_id: null,
      updated_at: '2026-11-11T08:02:00Z',
    });
    monitorState.events = analyzed();
    await act(async () => root.render(tree()));

    expect(bindSpy).toHaveBeenCalledWith('wf-1', 48, expect.objectContaining({ rpsId: 'rps-1', throwOnError: true }));
    expect(node.textContent).not.toContain('RPS belum tersimpan untuk kursus ini');
    expect(node.textContent).not.toContain('Simpan sebagai RPS kursus');
  });

  it('AiCourseLayout hanya menampilkan Alert error dengan Coba lagi saat auto-sync ke server benar-benar gagal', async () => {
    vi.spyOn(courseService, 'findCourseByMoodleId').mockResolvedValue(null);
    vi.spyOn(workflowService, 'getActiveCourseBinding').mockReturnValue({
      workflowId: 'wf-1',
      rpsId: 'rps-1',
      pendingTargetSync: false,
    });
    vi.spyOn(workflowService, 'findWorkflowForCourse').mockResolvedValue(wf({ moodle_course_id: null }));
    const bindSpy = vi.spyOn(workflowService, 'bindWorkflowToCourse')
      .mockRejectedValueOnce(new Error('Koneksi server terputus'))
      .mockResolvedValueOnce(wf({ moodle_course_id: 48 }));
    vi.spyOn(rpsService, 'getRps').mockResolvedValue({ id: 'rps-1', filename: 'RPS SBD.pdf', status: 'ANALYZED' });

    monitorState.workflow = wf({ status: 'RUNNING', stage: 'instructor_review', moodle_course_id: null });
    monitorState.events = analyzed();

    await act(async () => root.render(
      <MemoryRouter initialEntries={['/course/48/ai']}>
        <Routes>
          <Route path="/course/:courseId/ai" element={<AiCourseLayout />}>
            <Route index element={<CourseOverviewPage />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    ));

    expect(bindSpy).toHaveBeenCalledTimes(1);
    expect(node.textContent).toContain('Gagal menghubungkan RPS ke kursus di server');
    expect(node.textContent).toContain('Koneksi server terputus');

    const retryBtn = [...node.querySelectorAll('button')].find((b) => b.textContent.includes('Coba lagi'));
    expect(retryBtn).toBeTruthy();
    await act(async () => {
      retryBtn.click();
    });

    expect(bindSpy).toHaveBeenCalledTimes(2);
    expect(node.textContent).not.toContain('Gagal menghubungkan RPS ke kursus di server');
  });
});
