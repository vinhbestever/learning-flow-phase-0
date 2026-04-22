import { formatStudentAnswerDisplay } from './formatStudentAnswer'

/** Fields needed to tell “có bài làm LMS” vs “chỉ có đề / chưa làm”. */
export type LmsQuestionAttemptFields = {
  questions_source?: string | null
  detail_result_id?: number | null
  is_correct?: number | null
  is_failed?: boolean
  student_answer?: unknown
}

export function hasLmsQuestionSubmission(q: LmsQuestionAttemptFields): boolean {
  const studentStr = formatStudentAnswerDisplay(q.student_answer)
  return (
    q.detail_result_id != null
    || q.is_correct === 0
    || q.is_correct === 1
    || studentStr.length > 0
    || q.is_failed === true
    || q.questions_source === 'lms_practice_result_detail'
  )
}

/**
 * Kết quả theo dữ liệu LMS / gộp bài sai.
 * `not_submitted` = có đề nhưng không có dòng chi tiết bài làm cho câu này (thường là ngân hàng).
 * Có bài làm nhưng không có cờ đúng/sai (`is_correct` null, không `is_failed`) → mặc định coi là đúng.
 */
export function lmsQuestionOutcome(
  q: LmsQuestionAttemptFields,
): 'correct' | 'incorrect' | 'not_submitted' {
  if (!hasLmsQuestionSubmission(q)) return 'not_submitted'
  if (q.is_correct === 0 || q.is_failed) return 'incorrect'
  return 'correct'
}
