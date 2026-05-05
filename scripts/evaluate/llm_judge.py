from __future__ import annotations

import json
import random
import statistics


def _lesson_context_for_judge(lesson_id: int, student_context: dict) -> str:
    cand_map = {c["lesson_id"]: c for c in student_context["scored_candidates"]}
    c = cand_map.get(lesson_id)
    if not c:
        return "No candidate data available."

    lines = [
        f"Lesson: {c.get('title', 'Unknown')} | "
        f"{c.get('days_since_last_practice', '?')} days since last practice | "
        f"weakness={c.get('weakness_score', '?'):.2f} | "
        f"hw_status={c.get('homework_status', '?')}"
    ]
    for fq in (c.get("failed_text_questions") or [])[:3]:
        lines.append(
            f"  [FAILED] Q: {fq.get('question_text', '')[:80]} | "
            f"correct={fq.get('correct_answer')} | student={fq.get('student_answer')}"
        )
    for si in (c.get("worst_speaking_items") or [])[:3]:
        lines.append(
            f"  [SPEAKING/{si.get('lms_type')}] Q: {si.get('question', '')[:60]} | "
            f"said='{si.get('user_transcript', '')}' | score={si.get('score')} | type={si.get('answer_type')}"
        )
    for pq in (c.get("question_bank_preview") or [])[:2]:
        lines.append(f"  [PREVIEW] {pq.get('question_text', '')[:80]}")
    return "\n".join(lines)


_REASON_RUBRIC_PROMPT = """\
You are evaluating the "reason" field written by an AI homework-assignment system \
for a Vietnamese English learner (elementary level, ~10 years old).

STUDENT CONTEXT:
- Brainstorm (image→name visual targets) avg: {brainstorm_avg}/100 — CRITICAL weakness
- Free speaking avg: {free_speaking_avg}/100
- Pronunciation avg: {pronunciation_avg}/100
- Written homework accuracy: ~94% (strong)

HOMEWORK QUESTION BEING ASSIGNED:
- lesson: {lesson_title}
- skill_category: {skill_category}
- question_type: {question_type}
- question_text: {question_text}
- correct_answer: {correct_answer}

ACTUAL STUDENT DATA FOR THIS LESSON:
{lesson_context}

REASON FIELD TO EVALUATE:
"{reason}"

Rate on each dimension (1=poor, 5=excellent):
- specificity: Cites a specific wrong answer, transcript, or concrete error (not generic)
- timing: Mentions when the lesson was last practiced (days/weeks/months)
- data_accuracy: Consistent with the actual student data above (no invented facts)
- actionability: Helps teacher/student understand exactly what to work on and why
- language_quality: Natural Vietnamese (fluent, not machine-translated feel)

Return ONLY JSON: {{"specificity": N, "timing": N, "data_accuracy": N, "actionability": N, "language_quality": N, "comment": "one-sentence note in English"}}"""

_DIAGNOSTIC_RUBRIC_PROMPT = """\
You are evaluating a diagnostic analysis written by an AI model about a Vietnamese \
English learner's weaknesses. This diagnostic is used to brief a homework-selector agent.

ACTUAL STUDENT DATA:
- Brainstorm (image→name targets) avg: {brainstorm_avg}/100 — this is the CRITICAL weakness
- Free speaking avg: {free_speaking_avg}/100
- Pronunciation avg: {pronunciation_avg}/100
- Written homework accuracy: {homework_accuracy} (strong — do NOT flag this as a weakness)
- Total lessons: {total_lessons}, completed: {completed}
- Forgetting: most lessons were studied 7–120 days ago

DIAGNOSTIC TEXT (first 1200 chars):
{diagnostic}

Rate on each dimension (1=poor, 5=excellent):
- weakness_identification: Correctly identifies brainstorm/speaking as primary weakness \
(not written accuracy which is already strong)
- pattern_depth: Explains WHY failures happen, not just lists them
- actionability: Gives clear guidance the selector agent can act on
- specificity: Cites specific lesson titles, scores, or student transcripts

Return ONLY JSON: {{"weakness_identification": N, "pattern_depth": N, "actionability": N, "specificity": N, "comment": "one-sentence note in English"}}"""


def _openai_json(client, model: str, prompt: str) -> dict:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def evaluate_reasons_llm(
    homework_by_model: dict,
    student_context: dict,
    judge_model: str,
    models_to_eval: list[str],
    sample_n: int = 5,
) -> dict:
    import openai

    client = openai.OpenAI()
    summary = student_context["summary"]

    brainstorm_avg = summary.get("overall_brainstorm_score_avg", "?")
    free_speaking_avg = summary.get("overall_free_speaking_score_avg", "?")
    pronunciation_avg = summary.get("overall_pronunciation_score_avg", "?")
    homework_accuracy = next(
        iter(summary.get("overall_homework_skill_breakdown", {}).values()), {}
    ).get("accuracy", "?")
    total_lessons = summary.get("total_lessons", "?")
    completed = summary.get("lessons_by_status", {}).get("completed", "?")

    results: dict[str, dict] = {}

    for model_name in models_to_eval:
        model_data = homework_by_model["models"].get(model_name, {})
        hw = model_data.get("homework", [])
        diagnostic = model_data.get("diagnostic", "")

        print(f"  [{model_name}] judging reasons... ", end="", flush=True)

        sample = random.sample(hw, min(sample_n, len(hw)))
        reason_scores: list[dict] = []
        for q in sample:
            lesson_ctx = _lesson_context_for_judge(q["lesson_id"], student_context)
            prompt = _REASON_RUBRIC_PROMPT.format(
                brainstorm_avg=brainstorm_avg,
                free_speaking_avg=free_speaking_avg,
                pronunciation_avg=pronunciation_avg,
                lesson_title=q.get("lesson_title", ""),
                skill_category=q.get("skill_category", ""),
                question_type=q.get("question_type", ""),
                question_text=(q.get("question_text") or "")[:150],
                correct_answer=q.get("correct_answer", ""),
                lesson_context=lesson_ctx,
                reason=q.get("reason", ""),
            )
            try:
                scores = _openai_json(client, judge_model, prompt)
                scores["question_no"] = q.get("question_no")
                scores["reason_preview"] = (q.get("reason") or "")[:80]
            except Exception as exc:
                scores = {"question_no": q.get("question_no"), "error": str(exc)}
            reason_scores.append(scores)

        dims = ["specificity", "timing", "data_accuracy", "actionability", "language_quality"]
        valid = [s for s in reason_scores if "error" not in s]
        agg: dict[str, float | None] = {}
        if valid:
            for dim in dims:
                vals = [s[dim] for s in valid if isinstance(s.get(dim), (int, float))]
                agg[dim] = round(statistics.mean(vals), 2) if vals else None
            dim_vals = [v for v in agg.values() if v is not None]
            agg["overall"] = round(statistics.mean(dim_vals), 2) if dim_vals else None

        print(f"avg={agg.get('overall', 'N/A')} | judging diagnostic... ", end="", flush=True)

        diag_score: dict = {}
        try:
            diag_prompt = _DIAGNOSTIC_RUBRIC_PROMPT.format(
                brainstorm_avg=brainstorm_avg,
                free_speaking_avg=free_speaking_avg,
                pronunciation_avg=pronunciation_avg,
                homework_accuracy=homework_accuracy,
                total_lessons=total_lessons,
                completed=completed,
                diagnostic=diagnostic[:1200],
            )
            diag_score = _openai_json(client, judge_model, diag_prompt)
        except Exception as exc:
            diag_score = {"error": str(exc)}

        diag_dims = ["weakness_identification", "pattern_depth", "actionability", "specificity"]
        diag_vals = [diag_score.get(d) for d in diag_dims if isinstance(diag_score.get(d), (int, float))]
        diag_avg = round(statistics.mean(diag_vals), 2) if diag_vals else None
        print(f"diag={diag_avg}")

        results[model_name] = {
            "reason_scores_per_question": reason_scores,
            "reason_aggregated": agg,
            "diagnostic_score": diag_score,
            "diagnostic_avg": diag_avg,
        }

    return results
