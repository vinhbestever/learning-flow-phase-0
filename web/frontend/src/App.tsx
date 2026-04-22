import { Route, Routes } from 'react-router-dom'
import GenerateHomework from './pages/GenerateHomework'
import HistoryLessonDetail from './pages/HistoryLessonDetail'
import HomeworkResult from './pages/HomeworkResult'
import LearningHistory from './pages/LearningHistory'
import LessonDetail from './pages/LessonDetail'
import LessonList from './pages/LessonList'
import StudentLayout from './pages/StudentLayout'
import StudentProfile from './pages/StudentProfile'
import StudentsList from './pages/StudentsList'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<StudentsList />} />
      <Route path="/students/:studentId" element={<StudentLayout />}>
        <Route index element={<StudentProfile />} />
        <Route path="history" element={<LearningHistory />} />
        <Route path="history/:lessonId" element={<HistoryLessonDetail />} />
        <Route path="lessons" element={<LessonList />} />
        <Route path="lessons/:lessonId" element={<LessonDetail />} />
        <Route path="generate" element={<GenerateHomework />} />
        <Route path="homework" element={<HomeworkResult />} />
      </Route>
    </Routes>
  )
}
