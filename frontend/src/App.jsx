import { useState, useEffect, useCallback } from 'react';
import { APP_ROUTES } from './types/navigation';
import { DOSEN_PROFILE } from './types/auth';
import { getDefaultPathForRole, isPathAllowedForRole } from './utils/navigation';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import RequireAuth from './components/RequireAuth';
import { StatusPage } from './features/auth/StatusPage';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './features/auth/LoginPage';
import { ProfileModal } from './features/auth/components/ProfileModal';
import { DashboardPage } from './features/dashboard/DashboardPage';
import { RpsAnalysisPage } from './features/rps/RpsAnalysisPage';
import { UploadRpsModal } from './features/rps/components/UploadRpsModal';
import { RpsProgressModal } from './features/rps/components/RpsProgressModal';
import { CoursePlanPage } from './features/course-plan/CoursePlanPage';
import { GeneratePlanModal } from './features/course-plan/components/GeneratePlanModal';
import { PlanProgressModal } from './features/course-plan/components/PlanProgressModal';
import { PlanRevisionModal } from './features/course-plan/components/PlanRevisionModal';
import { WeekDetailPage } from './features/weekly-content/WeekDetailPage';
import { MaterialViewPage } from './features/weekly-content/MaterialViewPage';
import { GenerateContentModal } from './features/weekly-content/components/GenerateContentModal';
import { ContentProgressModal } from './features/weekly-content/components/ContentProgressModal';
import { ContentRevisionModal } from './features/weekly-content/components/ContentRevisionModal';
import { MoodlePublishModal } from './features/weekly-content/components/MoodlePublishModal';
import { MoodleSyncModal } from './features/weekly-content/components/MoodleSyncModal';
import { StudentCoursesPage } from './features/student/StudentCoursesPage';
import { StudentCourseDetailPage } from './features/student/StudentCourseDetailPage';
import { StudentWeekDetailPage } from './features/student/StudentWeekDetailPage';

function getInitialHasCourses() {
    const params = new URLSearchParams(window.location.search);
    const has = params.get('hasCourses');
    if (has === 'true')
        return true;
    if (has === 'false')
        return false;
    return false;
}
function getInitialPlanStage() {
    const params = new URLSearchParams(window.location.search);
    const stage = params.get('planStage');
    if (stage === 'empty' || stage === 'review' || stage === 'approved' || stage === 'published') {
        return stage;
    }
    return 'empty';
}
function getInitialContentStage() {
    const params = new URLSearchParams(window.location.search);
    const stage = params.get('contentStage');
    if (stage === 'empty' || stage === 'review' || stage === 'synced') {
        return stage;
    }
    return 'empty';
}
function ApprovedApplication() {
    const { user, logout } = useAuth();
    const location = useLocation();
    const routerNavigate = useNavigate();
    const currentPath = location.pathname;
    const activeRole = user?.role;
    const [dosenProfile, setDosenProfile] = useState(() => ({ ...DOSEN_PROFILE,
      ...(user?.role === 'dosen' ? { name: user.name, email: user.email,
        avatarInitial: user.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() } : {}) }));
    const [hasCourses, setHasCourses] = useState(getInitialHasCourses);
    const [activeModal, setActiveModal] = useState(null);
    const [coursePlanStage, setCoursePlanStage] = useState(getInitialPlanStage);
    const [weeklyContentStage, setWeeklyContentStage] = useState(getInitialContentStage);
    const [selectedWeek, setSelectedWeek] = useState(3);
    const [selectedMaterialId, setSelectedMaterialId] = useState('doc-week3-pdf');
    const [toasts, setToasts] = useState([]);
    const showToast = useCallback((message, type = 'info') => {
        const id = Date.now().toString() + Math.random().toString(36).substring(2, 6);
        setToasts((prev) => [...prev, { id, message, type }]);
    }, []);
    const dismissToast = useCallback((id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);
    const navigate = useCallback((path) => {
        if (path === '/login') logout();
        routerNavigate(path);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }, [routerNavigate, logout]);
    const navigateMaterial = useCallback((path) => {
        const studentPaths = {
            '/dashboard': '/student/courses',
            '/course-plan': '/student/course',
            '/weekly-content': '/student/week',
        };
        navigate(activeRole === 'mahasiswa' ? studentPaths[path] ?? path : path);
    }, [activeRole, navigate]);
    const handleResetDemo = useCallback(() => {
        setHasCourses(false);
        setCoursePlanStage('empty');
        setWeeklyContentStage('empty');
        setSelectedWeek(3);
        setSelectedMaterialId('doc-week3-pdf');
        navigate('/dashboard');
        showToast('Alur demo berhasil direset ke kondisi awal.', 'info');
    }, [navigate, showToast]);
    useEffect(() => {
        document.title = APP_ROUTES[currentPath]?.title ?? 'Halaman tidak ditemukan — LMS ITK';
    }, [currentPath]);
    const closeModal = useCallback(() => {
        setActiveModal(null);
    }, []);
    if (currentPath !== '/login' && (!APP_ROUTES[currentPath] || !isPathAllowedForRole(currentPath, activeRole))) {
        return <AppLayout currentPath={currentPath} activeRole={activeRole} dosenProfile={dosenProfile}
          onNavigate={navigate} onOpenModal={setActiveModal} toasts={toasts} onDismissToast={dismissToast}>
          <StatusPage forbidden={Boolean(APP_ROUTES[currentPath])} />
        </AppLayout>;
    }
    return (<AppLayout currentPath={currentPath} activeRole={activeRole} dosenProfile={dosenProfile} onNavigate={navigate}  onOpenModal={setActiveModal} toasts={toasts} onDismissToast={dismissToast}>
      {/* Route Views */}
      {currentPath === '/login' && (<LoginPage />)}

      {currentPath === '/dashboard' && (<DashboardPage hasCourses={hasCourses} onNavigate={navigate} onOpenModal={setActiveModal} onShowToast={showToast}/>)}

      {currentPath === '/rps-analysis' && (<RpsAnalysisPage onNavigate={navigate} onShowToast={showToast}/>)}

      {currentPath === '/course-plan' && (<CoursePlanPage stage={coursePlanStage} onStageChange={setCoursePlanStage} allWeeksGenerated={weeklyContentStage === 'review' || weeklyContentStage === 'synced'} onAutoGenerateAllWeeks={() => {
                setWeeklyContentStage('review');
            }} onSelectWeek={(week) => setSelectedWeek(week)} onNavigate={navigate} onOpenModal={setActiveModal} onShowToast={showToast}/>)}

      {currentPath === '/weekly-content' && (<WeekDetailPage stage={weeklyContentStage} weekNumber={selectedWeek} onStageChange={setWeeklyContentStage} onSelectMaterial={(id) => setSelectedMaterialId(id)} onNavigate={navigate} onOpenModal={setActiveModal} onShowToast={showToast}/>)}

      {currentPath === '/material-view' && (<MaterialViewPage documentId={selectedMaterialId} weekNumber={selectedWeek} onNavigate={navigateMaterial} onShowToast={showToast}/>)}

      {currentPath === '/student/courses' && (<StudentCoursesPage onNavigate={navigate} onShowToast={showToast}/>)}

      {currentPath === '/student/course' && (<StudentCourseDetailPage onNavigate={navigate} onShowToast={showToast}/>)}

      {currentPath === '/student/week' && (<StudentWeekDetailPage weekNumber={selectedWeek} onSelectMaterial={(id) => setSelectedMaterialId(id)} onNavigate={navigate} onShowToast={showToast}/>)}

      {/* Feature Modals */}
      <ProfileModal isOpen={activeModal === 'profile'} onClose={closeModal} profile={dosenProfile} onShowToast={showToast} onResetDemo={handleResetDemo} onSave={(name, email, teachingApproach, aiInstructions) => {
            setDosenProfile((prev) => {
                const initials = name
                    .split(' ')
                    .map((part) => part[0])
                    .filter(Boolean)
                    .slice(0, 2)
                    .join('')
                    .toUpperCase() || 'MC';
                return {
                    ...prev,
                    name,
                    email,
                    avatarInitial: initials,
                    teachingApproach,
                    aiInstructions,
                };
            });
        }}/>

      <UploadRpsModal isOpen={activeModal === 'upload-rps'} onClose={closeModal} onStartAnalysis={() => setActiveModal('rps-progress')}/>

      <RpsProgressModal isOpen={activeModal === 'rps-progress'} onClose={closeModal} onComplete={() => {
            setHasCourses(true);
            setCoursePlanStage('empty');
            setWeeklyContentStage('empty');
            closeModal();
            navigate('/rps-analysis');
            showToast('Dokumen RPS berhasil dianalisis.', 'success');
        }}/>

      <GeneratePlanModal isOpen={activeModal === 'generate-plan'} onClose={closeModal} onStartGenerate={() => setActiveModal('plan-progress')}/>

      <PlanProgressModal isOpen={activeModal === 'plan-progress'} onClose={closeModal} onComplete={() => {
            setCoursePlanStage('review');
            closeModal();
            showToast('Course Plan berhasil disusun oleh Agent AI.', 'success');
        }}/>

      <PlanRevisionModal isOpen={activeModal === 'plan-revision'} onClose={closeModal} onSubmitRevision={() => {
            showToast('Catatan revisi course plan dikirim ke Agent.', 'info');
            setActiveModal('plan-progress');
        }}/>

      <GenerateContentModal isOpen={activeModal === 'generate-content'} onClose={closeModal} onStartGenerate={() => setActiveModal('content-progress')}/>

      <ContentProgressModal isOpen={activeModal === 'content-progress'} onClose={closeModal} onComplete={() => {
            setWeeklyContentStage('review');
            closeModal();
            showToast('Draft materi dan tugas Minggu 03 berhasil disusun.', 'success');
        }}/>

      <ContentRevisionModal isOpen={activeModal === 'content-revision'} onClose={closeModal} onSubmitRevision={() => {
            showToast('Catatan revisi konten dikirim ke Agent.', 'info');
            setActiveModal('content-progress');
        }}/>

      <MoodlePublishModal isOpen={activeModal === 'moodle-publish'} onClose={closeModal} onExecute={() => setActiveModal('moodle-sync')}/>

      <MoodleSyncModal isOpen={activeModal === 'moodle-sync'} onClose={closeModal} onComplete={() => {
            setWeeklyContentStage('synced');
            setCoursePlanStage('published');
            closeModal();
            showToast('Konten Minggu 03 berhasil dipublikasikan & diverifikasi di Moodle ITK.', 'success');
        }}/>
    </AppLayout>);
}

export default function App() {
  const { user } = useAuth();
  return <Routes>
    <Route path="/login" element={<ApprovedApplication key="anonymous" />} />
    <Route element={<RequireAuth />}>
      <Route path="/" element={<Navigate to={getDefaultPathForRole(user?.role)} replace />} />
      <Route path="/my" element={<Navigate to={getDefaultPathForRole(user?.role)} replace />} />
      <Route path="/ai" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<ApprovedApplication key={user?.id} />} />
    </Route>
  </Routes>;
}
