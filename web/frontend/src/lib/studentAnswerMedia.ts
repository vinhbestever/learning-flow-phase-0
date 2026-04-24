/**
 * Derive playable audio URLs from LMS `student_answer` (bai_lam) and from
 * `choice_previews` for the option(s) the student selected (e.g. answer_audio_url).
 */

import type { ChoicePreview } from '../components/HomeworkQuestionRich'
import { formatStudentAnswerDisplay } from './formatStudentAnswer'

const AUDIO_IN_PATH = /\.(mp3|m4a|wav|ogg|aac|webm)(\?|#|$)/i

function isHttpAudioUrl(s: string): boolean {
  const t = s.trim()
  if (!/^https?:\/\//i.test(t)) return false
  return AUDIO_IN_PATH.test(t)
}

/** URLs embedded directly in the submission (e.g. voice upload). */
export function collectStudentSubmissionAudioUrls(value: unknown): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  const push = (raw: string) => {
    const t = raw.trim()
    if (!t || seen.has(t) || !isHttpAudioUrl(t)) return
    seen.add(t)
    out.push(t)
  }

  if (typeof value === 'string') {
    push(value)
    return out
  }
  if (!Array.isArray(value)) return out

  for (const item of value) {
    if (typeof item === 'string') push(item)
    else if (item != null && typeof item === 'object' && 'u' in item) {
      const u = (item as { u?: unknown }).u
      if (typeof u === 'string') push(u)
    }
  }
  return out
}

function norm(s: string) {
  return s.toLowerCase().replace(/\s+/g, ' ').trim()
}

function letterLeadingAnswer(flat: string): string | null {
  const m = flat.trim().match(/^([A-Za-z])(?:[\s.):,-]|$)/)
  return m ? m[1].toUpperCase() : null
}

/**
 * For multiple-choice with `answer_audio_url` on options, return audio file(s)
 * attached to the choice(s) matching the student's answer text or letter.
 */
export function audioUrlsFromMatchedChoices(
  studentAnswer: unknown,
  choicePreviews: ChoicePreview[] | null | undefined,
): string[] {
  if (!choicePreviews?.length) return []
  const flat = formatStudentAnswerDisplay(studentAnswer).trim()
  if (!flat) return []

  const nFlat = norm(flat)
  const segments = flat
    .split(/\s*,\s*/)
    .map((s) => s.trim())
    .filter(Boolean)
  const nSegments = segments.map(norm)
  const letterHit = letterLeadingAnswer(flat)

  const seen = new Set<string>()
  const out: string[] = []
  const addChoice = (c: ChoicePreview) => {
    for (const u of c.audio_urls || []) {
      if (u && !seen.has(u)) {
        seen.add(u)
        out.push(u)
      }
    }
  }

  for (const c of choicePreviews) {
    const auds = c.audio_urls || []
    if (!auds.length) continue
    const L = (c.letter || '').toUpperCase()
    if (
      L
      && (letterHit === L || segments.some((seg) => letterLeadingAnswer(seg) === L))
    ) {
      addChoice(c)
      continue
    }
    const ct = c.text ? norm(c.text) : ''
    if (ct && (nFlat === ct || nSegments.includes(ct))) addChoice(c)
  }
  return out
}

export function allStudentAnswerPlaybackUrls(
  studentAnswer: unknown,
  choicePreviews: ChoicePreview[] | null | undefined,
): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const u of collectStudentSubmissionAudioUrls(studentAnswer)) {
    if (!seen.has(u)) {
      seen.add(u)
      out.push(u)
    }
  }
  for (const u of audioUrlsFromMatchedChoices(studentAnswer, choicePreviews)) {
    if (!seen.has(u)) {
      seen.add(u)
      out.push(u)
    }
  }
  return out
}
