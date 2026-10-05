import { Navigate, Route, Routes } from 'react-router-dom';
import MoodleLayout from './components/MoodleLayout';
import RequireAuth from './components/RequireAuth';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import LoginPage from './pages/LoginPage';
import { NotFoundPage } from './pages/StatusPage';
// Moodle (dosen & mahasiswa)
import DashboardPage from './pages/moodle/DashboardPage';
import MyCoursesPage from './pages/moodle/MyCoursesPage';
import ProfilePage from './pages/moodle/ProfilePage';
import CourseLayout from './pages/moodle/course/CourseLayout';
import CourseViewPage from './pages/moodle/course/CourseViewPage';
import ParticipantsPage from './pages/moodle/course/ParticipantsPage';
import GradesPage from './pages/moodle/course/GradesPage';
import ActivityPage from './pages/moodle/course/ActivityPage';
// Generator Konten AI (khusus dosen)
import AiLayout from './pages/ai/AiLayout';
import AiDashboardPage from './pages/ai/AiDashboardPage';
import RpsPage from './pages/ai/RpsPage';
import RpsAnalysisPage from './pages/ai/RpsAnalysisPage';
import NewCoursePage from './pages/ai/NewCoursePage';
import TeachingProfilePage from './pages/ai/TeachingProfilePage';
import AiCourseLayout from './pages/ai/course/CourseLayout';
import CourseOverviewPage from './pages/ai/course/CourseOverviewPage';
import CoursePlanPage from './pages/ai/course/CoursePlanPage';
import CourseContentPage from './pages/ai/course/CourseContentPage';
import CourseReviewPage from './pages/ai/course/CourseReviewPage';
import CourseMoodlePage from './pages/ai/course/CourseMoodlePage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<MoodleLayout />}>
          <Route index element={<Navigate to="/my" replace />} />
          <Route path="my" element={<DashboardPage />} />
          <Route path="my/courses" element={<MyCoursesPage />} />
          <Route path="user/profile" element={<ProfilePage />} />

          <Route path="course/:courseId" element={<CourseLayout />}>
            <Route index element={<CourseViewPage />} />
            <Route path="participants" element={<ParticipantsPage />} />
            <Route path="grades" element={<GradesPage />} />
            <Route path="mod/:cmid" element={<ActivityPage />} />
          </Route>

          <Route element={<RequireAuth roles={['dosen']} />}>
            <Route path="ai" element={<AiLayout />}>
              <Route index element={<AiDashboardPage />} />
              <Route path="rps" element={<RpsPage />} />
              <Route path="rps/:rpsId" element={<RpsAnalysisPage />} />
              <Route path="profile" element={<TeachingProfilePage />} />
              <Route path="courses/new" element={<NewCoursePage />} />
              <Route path="courses/:courseId" element={<AiCourseLayout />}>
                <Route index element={<CourseOverviewPage />} />
                <Route path="plan" element={<CoursePlanPage />} />
                <Route path="content" element={<CourseContentPage />} />
                <Route path="review" element={<CourseReviewPage />} />
                <Route path="moodle" element={<CourseMoodlePage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
