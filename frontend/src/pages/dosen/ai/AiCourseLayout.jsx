import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { findCourseByMoodleId } from '../../../services/courseService';
import { getWorkflowPlan } from '../../../services/coursePlanService';
import { listWorkflowContents } from '../../../services/contentService';
import { listExecutions } from '../../../services/executionService';
import { listWorkflowVerifications } from '../../../services/verificationService';
import { useApi } from '../../../hooks/useApi';
import { useOnChange } from '../../../hooks/useOnChange';
import { useMoodleCourse } from '../../../hooks/useMoodleCourse';
import { useWorkflowMonitor } from '../../../hooks/useWorkflowMonitor';
import { getRps } from '../../../services/rpsService';
import {
  bindWorkflowToCourse,
  findWorkflowForCourse,
  getActiveCourseBinding,
  moodleCourseIdOf,
  saveActiveCourseBinding,
} from '../../../services/workflowService';
import { isWorkflowBusy } from '../../../utils/workflowStatus';
import { COURSE_API_AVAILABLE } from '../../../services/config';
import { Alert, Badge, Card, ErrorAlert, ErrorBoundary, Spinner } from '../../../components/ui';
import WorkflowEventTimeline from '../../../components/ai/WorkflowEventTimeline';
import WorkflowStatusBadge from '../../../components/ai/WorkflowStatusBadge';
import WorkflowStepper from '../../../components/ai/WorkflowStepper';
import { ForbiddenPage } from '../../StatusPage';
import WorkflowLayout from './WorkflowLayout';

/**
 * Tab "Generator AI" di halaman kursus. Memakai satu bar stepper interaktif di atas
 * serta panel "Aktivitas agent" bawaan pada seluruh tahap (kecuali halaman /workflows).
 * Sesuai design-api.md §17: ambil initial state via HTTP dulu, baru pakai event stream.
 */
function CourseProjectLayout() {
  const { course: moodleCourse, isTeacher } = useMoodleCourse() ?? {};
  const params = useParams();
  const courseIdParam = params.courseId;
  const moodleId = moodleCourseIdOf(moodleCourse) || (Number.isInteger(Number(courseIdParam)) && Number(courseIdParam) > 0 ? Number(courseIdParam) : null);
  const courseLookupKey = moodleId || courseIdParam;

  // Status workflow dapat dibuka walau kursus ini belum punya project, mis. dari tautan di daftar RPS.
  const onStatusPage = useLocation().pathname.endsWith('/workflows');
  // Naik setiap ada event; halaman anak memakainya sebagai dependency untuk reload.
  const [version, setVersion] = useState(0);

  const { data: dbCourse, error, loading, reload } = useApi(async () => {
    if (!courseLookupKey) return null;
    return findCourseByMoodleId(courseLookupKey);
  }, [courseLookupKey]);

  // ?rps=<id>: hasil analisis RPS dari daftar RPS, walau kursus ini belum punya project.
  const [searchParams] = useSearchParams();
  const rpsParam = searchParams.get('rps');
  const workflowParam = searchParams.get('workflow');

  // Kumpulkan seluruh alias identifier yang mungkin milik kursus ini (angka, string ID, shortname)
  const courseKeys = [moodleId, courseIdParam, dbCourse?.id, dbCourse?.shortname, moodleCourse?.id, moodleCourse?.shortname].filter(Boolean);
  const courseKeysKey = courseKeys.join(',');

  // Binding aktif kursus ini yang tersimpan (FE-10 / RPS overwrite persistence)
  const activeBinding = getActiveCourseBinding(...courseKeys);

  // Cari workflow yang menargetkan kursus Moodle ini (FE-10 / FE-11)
  const activeWfQuery = useApi(
    () => (courseKeys.length ? findWorkflowForCourse(...courseKeys).catch(() => null) : null),
    [courseKeysKey, version]
  );
  const activeWorkflow = activeWfQuery.data;

  // Workflow yang course target-nya kursus ini di server: sumber bersama bagi semua dosen kursus ini.
  const serverWorkflow = moodleId && Number(activeWorkflow?.moodle_course_id) === moodleId ? activeWorkflow : null;

  // Binding di browser mengikuti server begitu server punya course target untuk kursus ini, agar tidak ada
  // browser yang tetap memakai RPS lama sementara dosen lain melihat RPS yang berbeda.
  // Jika browser baru saja mengunggah RPS dan masih menunggu sinkronisasi target, jangan timpa balik.
  useEffect(() => {
    if (!courseKeys.length || !serverWorkflow?.id) return;
    if (activeBinding?.pendingTargetSync && activeBinding.workflowId && activeBinding.workflowId !== serverWorkflow.id) {
      return;
    }
    if (activeBinding?.workflowId !== serverWorkflow.id) {
      saveActiveCourseBinding(moodleId || courseIdParam, {
        workflowId: serverWorkflow.id,
        rpsId: serverWorkflow.rps_id,
        pendingTargetSync: false,
      }, courseKeys);
    }
  }, [moodleId, courseIdParam, serverWorkflow?.id, serverWorkflow?.rps_id, activeBinding?.workflowId, activeBinding?.pendingTargetSync, courseKeysKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fallback metadata kursus dari Moodle jika belum tercatat di database internal /courses
  const baseCourse = dbCourse ?? (moodleCourse ? {
    moodle_course_id: moodleCourse.id,
    shortname: moodleCourse.shortname,
    fullname: moodleCourse.fullname,
    name: moodleCourse.fullname,
    code: moodleCourse.shortname,
  } : null);

  const pendingLocalWorkflowId = activeBinding?.pendingTargetSync ? activeBinding.workflowId : null;
  const effectiveWorkflowId = workflowParam
    ?? pendingLocalWorkflowId
    ?? serverWorkflow?.id
    ?? activeBinding?.workflowId
    ?? activeWorkflow?.id
    ?? baseCourse?.workflow_id
    ?? null;

  // Workflow project: dari project bila ada, atau dari RPS-nya (GET /rps/{id}); dipantau real-time (FE-10.2).
  const projectRps = useApi(
    () => (!effectiveWorkflowId && (rpsParam || (!activeBinding?.rpsId && baseCourse?.rps_id))
      ? getRps(rpsParam || baseCourse.rps_id).catch(() => null)
      : null),
    [effectiveWorkflowId, rpsParam, activeBinding?.rpsId, baseCourse?.rps_id],
  );

  const workflowId = effectiveWorkflowId ?? projectRps.data?.workflow_id ?? null;

  const effectiveRpsId = rpsParam
    ?? (activeBinding?.pendingTargetSync ? activeBinding.rpsId : serverWorkflow?.rps_id)
    ?? serverWorkflow?.rps_id
    ?? activeBinding?.rpsId
    ?? activeWorkflow?.rps_id
    ?? projectRps.data?.id
    ?? (!activeBinding?.rpsId ? baseCourse?.rps_id : null)
    ?? null;

  const course = baseCourse ? {
    ...baseCourse,
    rps_id: effectiveRpsId,
    workflow_id: workflowId,
  } : null;

  const monitor = useWorkflowMonitor(workflowId);
  const { reload: reloadWorkflow, workflow, events } = monitor;
  const effectiveWorkflow = workflow ?? activeWorkflow ?? null;

  const progressSnapshot = useApi(async () => {
    if (!workflowId) return { plan: null, contents: null, executions: null, verifications: null };
    const [plan, contents, executions, verifications] = await Promise.all([
      getWorkflowPlan(workflowId).catch(() => null),
      listWorkflowContents(workflowId).catch(() => null),
      listExecutions(workflowId).catch(() => null),
      listWorkflowVerifications(workflowId).catch(() => null),
    ]);
    return { plan, contents, executions, verifications };
  }, [workflowId, version]);

  const progressSignature = effectiveWorkflow
    ? `${effectiveWorkflow.status}|${effectiveWorkflow.stage ?? ''}|${effectiveWorkflow.updated_at ?? ''}|${events.length}`
    : null;
  const { reload: reloadSnapshot } = progressSnapshot;
  useOnChange(progressSignature, () => {
    reloadSnapshot({ silent: true });
  }, 300);

  const { reload: reloadActiveWf } = activeWfQuery;
  const refresh = useCallback(() => {
    setVersion((v) => v + 1);
    reloadWorkflow();
    reloadSnapshot({ silent: true });
    reloadActiveWf({ silent: true });
    return reload({ silent: true });
  }, [reload, reloadWorkflow, reloadSnapshot, reloadActiveWf, setVersion]);

  const busy = isWorkflowBusy(effectiveWorkflow);
  const prevBusyRef = useRef(busy);
  const syncingRef = useRef(false);
  const lastSyncAttemptKeyRef = useRef(null);
  const [syncFailure, setSyncFailure] = useState(null);
  const [retryingSync, setRetryingSync] = useState(false);

  const isPendingBinding = Boolean(
    activeBinding?.pendingTargetSync
    && activeBinding?.workflowId
    && activeBinding.workflowId === workflowId
  );
  const serverTargetId = effectiveWorkflow?.id === workflowId ? effectiveWorkflow.moodle_course_id : undefined;
  const needsTargetSync = Boolean(
    moodleId
    && workflowId
    && !workflowParam
    && !activeWfQuery.loading
    && effectiveWorkflow?.id === workflowId
    && !busy
    && (isPendingBinding || serverTargetId == null)
    && (isPendingBinding || Number(serverTargetId) !== moodleId)
  );
  const syncAttemptKey = needsTargetSync
    ? `${workflowId}:${moodleId}:${effectiveWorkflow?.updated_at ?? ''}:${effectiveWorkflow?.status ?? ''}:${effectiveWorkflow?.stage ?? ''}:${isPendingBinding ? 'pending' : 'null'}`
    : null;

  const syncCourseTarget = useCallback(async ({ manual = false } = {}) => {
    if (!moodleId || !workflowId || syncingRef.current) return;
    syncingRef.current = true;
    if (manual) setRetryingSync(true);
    try {
      const updated = await bindWorkflowToCourse(workflowId, moodleId, {
        rpsId: effectiveRpsId,
        aliases: courseKeys,
        throwOnError: true,
      });
      if (updated && Number(updated.moodle_course_id) === moodleId && !isWorkflowBusy(updated)) {
        saveActiveCourseBinding(moodleId || courseIdParam, {
          workflowId,
          rpsId: effectiveRpsId ?? updated.rps_id,
          pendingTargetSync: false,
        }, courseKeys);
      }
      setSyncFailure(null);
      reloadWorkflow();
      reloadActiveWf({ silent: true });
    } catch (err) {
      setSyncFailure({ workflowId, error: err });
    } finally {
      syncingRef.current = false;
      if (manual) setRetryingSync(false);
    }
  }, [moodleId, courseIdParam, workflowId, effectiveRpsId, courseKeysKey, reloadWorkflow, reloadActiveWf]); // eslint-disable-line react-hooks/exhaustive-deps

  // Saat workflow baru selesai dari proses background, tarik detail workflow terbaru agar moodle_course_id
  // yang mungkin tertimpa oleh task background langsung terdeteksi tanpa menunggu interval polling.
  useEffect(() => {
    const wasBusy = prevBusyRef.current;
    prevBusyRef.current = busy;
    if (wasBusy && !busy && workflowId) {
      reloadWorkflow();
      reloadActiveWf({ silent: true });
    }
  }, [busy, workflowId, reloadWorkflow, reloadActiveWf]);

  // Sinkronkan course target di server secara otomatis setelah proses background workflow berhenti.
  useEffect(() => {
    if (!needsTargetSync || !syncAttemptKey || syncingRef.current) return;
    if (lastSyncAttemptKeyRef.current === syncAttemptKey) return;
    lastSyncAttemptKeyRef.current = syncAttemptKey;
    syncCourseTarget();
  }, [needsTargetSync, syncAttemptKey, syncCourseTarget]);

  const syncError = needsTargetSync && syncFailure && syncFailure.workflowId === workflowId ? syncFailure.error : null;
  const handleRetrySync = () => {
    lastSyncAttemptKeyRef.current = null;
    syncCourseTarget({ manual: true });
  };
  const [activityOpen, setActivityOpen] = useState(true);

  if (!isTeacher) return <ForbiddenPage />;
  if (loading && !course) return <Spinner />;
  if (error && !course) return <ErrorAlert error={error} />;
  if (!course && onStatusPage) return <Outlet context={{ course: null, events: [], version, refresh }} />;

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">
          Generator konten AI · RPS {course.code ?? course.shortname} — {course.name ?? course.fullname}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <NavLink
            to=""
            end
            className={({ isActive }) => `btn btn--xs ${isActive ? 'btn--secondary font-semibold' : 'btn--ghost'}`}
          >
            Ringkasan
          </NavLink>
          {effectiveWorkflow ? <WorkflowStatusBadge workflow={effectiveWorkflow} /> : <Badge>Belum dimulai</Badge>}
        </div>
      </div>
      <WorkflowStepper
        workflow={effectiveWorkflow}
        events={events}
        plan={progressSnapshot.data?.plan ?? null}
        contents={progressSnapshot.data?.contents ?? null}
        executions={progressSnapshot.data?.executions ?? null}
        verifications={progressSnapshot.data?.verifications ?? null}
      />

      {/* Riwayat aktivitas agent (LLM) selalu di kolom kanan seluruh tahap; layar sempit menumpuk di bawah. */}
      <div className={onStatusPage ? '' : 'grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,340px)] lg:items-start'}>
      <div className="min-w-0">
      {syncError && (
        <Alert
          tone="danger"
          title="Gagal menghubungkan RPS ke kursus di server"
          onClose={() => setSyncFailure(null)}
        >
          <p>{syncError?.message || String(syncError)}</p>
          <button
            type="button"
            className="btn btn--secondary btn--sm mt-2"
            disabled={retryingSync}
            onClick={handleRetrySync}
          >
            {retryingSync ? 'Menghubungkan…' : 'Coba lagi'}
          </button>
        </Alert>
      )}

      <ErrorBoundary>
        <Outlet context={{
          course,
          moodleCourse,
          workflow: effectiveWorkflow,
          workflowId,
          events,
          plan: progressSnapshot.data?.plan ?? null,
          contents: progressSnapshot.data?.contents ?? null,
          executions: progressSnapshot.data?.executions ?? null,
          verifications: progressSnapshot.data?.verifications ?? null,
          connection: monitor.connection,
          version,
          refresh,
          initialRpsId: dbCourse?.rps_id ?? null,
          // Pencarian workflow kursus (course target) masih berjalan: halaman anak menunggu, bukan menganggap kosong.
          workflowLoading: activeWfQuery.loading && !workflowId,
        }} />
      </ErrorBoundary>
      </div>

      {!onStatusPage && (
        <section className="min-w-0 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto" aria-label="Aktivitas agent">
          <Card
            title="Aktivitas agent"
            actions={(
              <div className="flex flex-wrap items-center gap-2">
                {busy && <Badge tone="info">Berjalan</Badge>}
                <Link to="workflows" className="btn btn--ghost btn--xs">
                  Detail workflow →
                </Link>
                <button
                  type="button"
                  className="btn btn--ghost btn--xs"
                  aria-expanded={activityOpen}
                  onClick={() => setActivityOpen((open) => !open)}
                >
                  {activityOpen ? 'Sembunyikan' : `Tampilkan (${events.length})`}
                </button>
              </div>
            )}
          >
            {activityOpen ? (
              <WorkflowEventTimeline events={events} />
            ) : (
              <p className="text-sm text-muted">
                {events.length > 0
                  ? `Aktivitas terbaru: ${events[events.length - 1]?.message || events[events.length - 1]?.event} (${events.length} catatan)`
                  : 'Belum ada aktivitas agent.'}
              </p>
            )}
          </Card>
        </section>
      )}
      </div>
    </>
  );
}

export default function AiCourseLayout() {
  return COURSE_API_AVAILABLE ? <CourseProjectLayout /> : <WorkflowLayout />;
}
