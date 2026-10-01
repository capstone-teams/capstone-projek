import { useState, useEffect, useCallback } from 'react'
import type { AppPath, ModalType } from './types/navigation'
import { APP_ROUTES } from './types/navigation'
import type { AuthUser } from './types/auth'
import type { CoursePlanStage, WeeklyContentStage } from './types/course'
import {
  getDefaultPathForRole,
  getPostLoginPath,
  resolveAppPath,
  resolveRouteAccess,
} from './utils/navigation'
import { useAuth } from './hooks/useAuth'
import { getInitials } from './services/authService'

import { AppLayout } from './components/layout/AppLayout'
import type { ToastItem } from './components/ui/Toast'

import { LoginPage } from './features/auth/LoginPage'
import { ProfileModal } from './features/auth/components/ProfileModal'
import { DashboardPage } from './features/dashboard/DashboardPage'
import { RpsAnalysisPage } from './features/rps/RpsAnalysisPage'
import { UploadRpsModal } from './features/rps/components/UploadRpsModal'
import { RpsProgressModal } from './features/rps/components/RpsProgressModal'
import { CoursePlanPage } from './features/course-plan/CoursePlanPage'
import { GeneratePlanModal } from './features/course-plan/components/GeneratePlanModal'
import { PlanProgressModal } from './features/course-plan/components/PlanProgressModal'
import { PlanRevisionModal } from './features/course-plan/components/PlanRevisionModal'
import { WeekDetailPage } from './features/weekly-content/WeekDetailPage'
import { MaterialViewPage } from './features/weekly-content/MaterialViewPage'
import { GenerateContentModal } from './features/weekly-content/components/GenerateContentModal'
import { ContentProgressModal } from './features/weekly-content/components/ContentProgressModal'
import { ContentRevisionModal } from './features/weekly-content/components/ContentRevisionModal'
import { MoodlePublishModal } from './features/weekly-content/components/MoodlePublishModal'
import { MoodleSyncModal } from './features/weekly-content/components/MoodleSyncModal'
import { StudentCoursesPage } from './features/student/StudentCoursesPage'
import { StudentCourseDetailPage } from './features/student/StudentCourseDetailPage'
import { StudentWeekDetailPage } from './features/student/StudentWeekDetailPage'
import { NotFoundPage } from './features/errors/NotFoundPage'
import { UnauthorizedPage } from './features/errors/UnauthorizedPage'

function getInitialPath(): AppPath {
  return resolveAppPath(window.location.pathname)
}

function getInitialHasCourses(): boolean {
  const params = new URLSearchParams(window.location.search)
  const has = params.get('hasCourses')
  if (has === 'true') return true
  if (has === 'false') return false
  return false
}

function getInitialPlanStage(): CoursePlanStage {
  const params = new URLSearchParams(window.location.search)
  const stage = params.get('planStage') as CoursePlanStage
  if (stage === 'empty' || stage === 'review' || stage === 'approved' || stage === 'published') {
    return stage
  }
  return 'empty'
}

function getInitialContentStage(): WeeklyContentStage {
  const params = new URLSearchParams(window.location.search)
  const stage = params.get('contentStage') as WeeklyContentStage
  if (stage === 'empty' || stage === 'review' || stage === 'synced') {
    return stage
  }
  return 'empty'
}

export default function App() {
  const { user, logout, updateProfile } = useAuth()
  // The path the user asked for. What is rendered is decided by the route guard,
  // so a protected path stays remembered while the login page is shown.
  const [requestedPath, setRequestedPath] = useState<AppPath>(getInitialPath)
  const routeDecision = resolveRouteAccess(requestedPath, user)
  const currentPath = routeDecision.path
  const homePath = user ? getDefaultPathForRole(user.role) : '/login'
  const [hasCourses, setHasCourses] = useState<boolean>(getInitialHasCourses)
  const [activeModal, setActiveModal] = useState<ModalType>(null)
  const [coursePlanStage, setCoursePlanStage] = useState<CoursePlanStage>(getInitialPlanStage)
  const [weeklyContentStage, setWeeklyContentStage] = useState<WeeklyContentStage>(getInitialContentStage)
  const [selectedWeek, setSelectedWeek] = useState<number>(3)
  const [selectedMaterialId, setSelectedMaterialId] = useState<string>('doc-week3-pdf')
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const showToast = useCallback((message: string, type: 'info' | 'success' = 'info') => {
    const id = Date.now().toString() + Math.random().toString(36).substring(2, 6)
    setToasts((prev) => [...prev, { id, message, type }])
  }, [])

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const navigate = useCallback((path: AppPath) => {
    setRequestedPath(path)
    window.history.pushState(null, '', path)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  const resetDemoState = useCallback(() => {
    setHasCourses(false)
    setCoursePlanStage('empty')
    setWeeklyContentStage('empty')
    setSelectedWeek(3)
    setSelectedMaterialId('doc-week3-pdf')
  }, [])

  const handleResetDemo = useCallback(() => {
    resetDemoState()
    navigate('/dashboard')
    showToast('Alur demo berhasil direset ke kondisi awal.', 'info')
  }, [navigate, resetDemoState, showToast])

  const handleLoginSuccess = useCallback(
    (signedIn: AuthUser) => {
      navigate(getPostLoginPath(signedIn, requestedPath))
    },
    [navigate, requestedPath],
  )

  const handleLogout = useCallback(async () => {
    await logout()
    resetDemoState()
    navigate('/login')
  }, [logout, navigate, resetDemoState])

  // Keep the address bar and title in line with the guarded route.
  // Unknown URLs keep their address while the not-found page is shown.
  useEffect(() => {
    if (resolveAppPath(window.location.pathname) !== currentPath) {
      window.history.replaceState(null, '', currentPath)
    }
    document.title = APP_ROUTES[currentPath].title
  }, [currentPath])

  // Listen to browser Back/Forward navigation
  useEffect(() => {
    const handlePopState = () => {
      setRequestedPath(resolveAppPath(window.location.pathname))
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  const closeModal = useCallback(() => {
    setActiveModal(null)
  }, [])

  return (
    <AppLayout
      currentPath={currentPath}
      currentUser={user}
      onNavigate={navigate}
      onLogout={handleLogout}
      onOpenModal={setActiveModal}
      toasts={toasts}
      onDismissToast={dismissToast}
    >
      {/* Route Views */}
      {currentPath === '/login' && (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}

      {currentPath === '/unauthorized' && (
        <UnauthorizedPage
          role={user?.role ?? null}
          homePath={homePath}
          onNavigate={navigate}
          onLogout={handleLogout}
        />
      )}

      {currentPath === '/not-found' && (
        <NotFoundPage homePath={homePath} onNavigate={navigate} />
      )}

      {currentPath === '/dashboard' && (
        <DashboardPage
          hasCourses={hasCourses}
          onNavigate={navigate}
          onOpenModal={setActiveModal}
          onShowToast={showToast}
        />
      )}

      {currentPath === '/rps-analysis' && (
        <RpsAnalysisPage
          onNavigate={navigate}
          onShowToast={showToast}
        />
      )}

      {currentPath === '/course-plan' && (
        <CoursePlanPage
          stage={coursePlanStage}
          onStageChange={setCoursePlanStage}
          allWeeksGenerated={weeklyContentStage === 'review' || weeklyContentStage === 'synced'}
          onAutoGenerateAllWeeks={() => {
            setWeeklyContentStage('review')
          }}
          onSelectWeek={(week) => setSelectedWeek(week)}
          onNavigate={navigate}
          onOpenModal={setActiveModal}
          onShowToast={showToast}
        />
      )}

      {currentPath === '/weekly-content' && (
        <WeekDetailPage
          stage={weeklyContentStage}
          weekNumber={selectedWeek}
          onStageChange={setWeeklyContentStage}
          onSelectMaterial={(id) => setSelectedMaterialId(id)}
          onNavigate={navigate}
          onOpenModal={setActiveModal}
          onShowToast={showToast}
        />
      )}

      {currentPath === '/material-view' && (
        <MaterialViewPage
          documentId={selectedMaterialId}
          weekNumber={selectedWeek}
          onNavigate={navigate}
          onShowToast={showToast}
        />
      )}

      {currentPath === '/student/courses' && (
        <StudentCoursesPage onNavigate={navigate} onShowToast={showToast} />
      )}

      {currentPath === '/student/course' && (
        <StudentCourseDetailPage
          onNavigate={navigate}
          onShowToast={showToast}
        />
      )}

      {currentPath === '/student/week' && (
        <StudentWeekDetailPage
          weekNumber={selectedWeek}
          onSelectMaterial={(id) => setSelectedMaterialId(id)}
          onNavigate={navigate}
          onShowToast={showToast}
        />
      )}

      {/* Feature Modals */}
      {user?.role === 'INSTRUCTOR' && (
        <ProfileModal
          isOpen={activeModal === 'profile'}
          onClose={closeModal}
          profile={user.profile}
          onShowToast={showToast}
          onResetDemo={handleResetDemo}
          onSave={(name, email, teachingApproach, aiInstructions) => {
            updateProfile({
              name,
              email,
              avatarInitial: getInitials(name),
              teachingApproach,
              aiInstructions,
            })
          }}
        />
      )}

      <UploadRpsModal
        isOpen={activeModal === 'upload-rps'}
        onClose={closeModal}
        onStartAnalysis={() => setActiveModal('rps-progress')}
      />

      <RpsProgressModal
        isOpen={activeModal === 'rps-progress'}
        onClose={closeModal}
        onComplete={() => {
          setHasCourses(true)
          setCoursePlanStage('empty')
          setWeeklyContentStage('empty')
          closeModal()
          navigate('/rps-analysis')
          showToast('Dokumen RPS berhasil dianalisis.', 'success')
        }}
      />

      <GeneratePlanModal
        isOpen={activeModal === 'generate-plan'}
        onClose={closeModal}
        onStartGenerate={() => setActiveModal('plan-progress')}
      />

      <PlanProgressModal
        isOpen={activeModal === 'plan-progress'}
        onClose={closeModal}
        onComplete={() => {
          setCoursePlanStage('review')
          closeModal()
          showToast('Course Plan berhasil disusun oleh Agent AI.', 'success')
        }}
      />

      <PlanRevisionModal
        isOpen={activeModal === 'plan-revision'}
        onClose={closeModal}
        onSubmitRevision={() => {
          showToast('Catatan revisi course plan dikirim ke Agent.', 'info')
          setActiveModal('plan-progress')
        }}
      />

      <GenerateContentModal
        isOpen={activeModal === 'generate-content'}
        onClose={closeModal}
        onStartGenerate={() => setActiveModal('content-progress')}
      />

      <ContentProgressModal
        isOpen={activeModal === 'content-progress'}
        onClose={closeModal}
        onComplete={() => {
          setWeeklyContentStage('review')
          closeModal()
          showToast('Draft materi dan tugas Minggu 03 berhasil disusun.', 'success')
        }}
      />

      <ContentRevisionModal
        isOpen={activeModal === 'content-revision'}
        onClose={closeModal}
        onSubmitRevision={() => {
          showToast('Catatan revisi konten dikirim ke Agent.', 'info')
          setActiveModal('content-progress')
        }}
      />

      <MoodlePublishModal
        isOpen={activeModal === 'moodle-publish'}
        onClose={closeModal}
        onExecute={() => setActiveModal('moodle-sync')}
      />

      <MoodleSyncModal
        isOpen={activeModal === 'moodle-sync'}
        onClose={closeModal}
        onComplete={() => {
          setWeeklyContentStage('synced')
          setCoursePlanStage('published')
          closeModal()
          showToast('Konten Minggu 03 berhasil dipublikasikan & diverifikasi di Moodle ITK.', 'success')
        }}
      />
    </AppLayout>
  )
}
