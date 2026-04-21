# Homework Agent Pipeline — Tài liệu hệ thống

## Tổng quan

Pipeline tự động tạo bộ 15 câu bài tập cá nhân hóa cho học sinh, dựa trên lịch sử học tập thực tế. Hệ thống ưu tiên các bài học mà học sinh đang **yếu** hoặc **đang quên** theo đường cong Ebbinghaus.

---

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────┐
│                   DỮ LIỆU ĐẦU VÀO                       │
│  data/*.json  (LMS results, Digital Teacher sessions)   │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │     preprocess.py          │  (Python thuần)
              │  + export_questions.py     │
              └─────────────┬─────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                                   ▼
  output/student_context.json     output/questions_export.json
  (profile + scored_candidates)   (toàn bộ câu hỏi đã học)
          │                                   │
          └─────────────┬─────────────────────┘
                        │
          ┌─────────────▼─────────────┐
          │   context_builder.py       │  (Python thuần, không LLM)
          │   Tiering + Filtering      │
          └─────────────┬─────────────┘
                        │
          ┌─────────────┼─────────────────┐
          ▼                               ▼
  tiered_candidates[]           question_pool[]
  (≤15 bài, có signal_type)     (~200-300 câu text-only)
          │
          └─────────────┬─────────────────┘
                        │
          ┌─────────────▼─────────────┐
          │   Diagnostic Agent         │  GPT-4o | temp=0.4
          │   (plain text output)      │
          └─────────────┬─────────────┘
                        │
              output/diagnostic_output.txt
              (~600 words phân tích)
                        │
          ┌─────────────▼─────────────┐
          │   Selector Agent           │  GPT-4o | temp=0 | json_schema
          │   (structured output)      │
          └─────────────┬─────────────┘
                        │
              output/homework_assignment.json
              (15 câu bài tập cá nhân hóa)
```

---

## Chi tiết từng bước

### Bước 1 — Tiền xử lý dữ liệu (đã có sẵn)

**Script:** `preprocess.py` → `output/student_context.json`

Tính toán cho từng bài học:
- `forgetting_score`: Ebbinghaus `1 - e^(-t/S)`, S=1 ngày. Bài > 7 ngày → score ≈ 1.0
- `weakness_score`: tổng hợp có trọng số (bài tập 35% + luyện tập 15% + free speaking 50%)
- `composite_priority_score`: `0.5 × forgetting + 0.5 × weakness`
- `scored_candidates`: top 20 bài theo composite score, kèm failed questions + worst speaking items

**Script:** `export_questions.py` → `output/questions_export.json`

Trích xuất toàn bộ câu hỏi từ dữ liệu gốc, phân loại:
- `pronunciation_drills`: bài đọc phát âm scripted
- `free_speaking`: câu hỏi nói tự do (open-ended)
- `interactive`: bài tập tương tác non-audio (single_choice, fill_paragraph, matching)
- `homework.bai_tap` / `homework.luyen_tap`: câu hỏi bài tập LMS

---

### Bước 2 — Context Builder (`agents/context_builder.py`)

**Không dùng LLM.** Chạy hoàn toàn bằng Python.

**Tiering candidates:**

| Tier | Điều kiện | Ý nghĩa |
|------|-----------|---------|
| `critical` | `weakness_score > 0.5` | Học sinh thực sự yếu |
| `spaced_rep` | `days_since > 14` VÀ `weakness_score ≤ 0.5` | Biết rồi nhưng đang quên |
| `maintenance` | Còn lại | Ổn định, nhắc nhở nhẹ |

**Greedy diversity selection:**
- Lặp qua từng tier theo thứ tự critical → spaced_rep → maintenance
- Trong mỗi vòng lặp, re-tính `adjusted_score = composite + 0.1 × new_skill_count` sau mỗi lần chọn → đảm bảo diversity boost là greedy, không phải batch
- Loại bài có < 2 câu text-renderable
- Loại câu hỏi có `requires_media=True` hoặc thiếu `question_text`
- Tổng cộng ≤ 15 candidates

**Output:** `tiered_candidates[]` + `question_pool[]` với metadata đính kèm:
- `signal_type`, `days_since`, `weakness_score` per question (để LLM có context viết `reason`)

---

### Bước 3 — Diagnostic Agent (`agents/diagnostic_agent.py`)

**Model:** GPT-4o | **Temperature:** 0.4 | **Output:** Plain text (~600 words)

**Input context:**
```
STUDENT SUMMARY
  Pronunciation avg: 86.96/100
  Free speaking avg: 30.71/100 (inaccordant: 16, incorrect: 34, correct: 48)

CRITICAL LESSONS:
  [CRITICAL] "Unit 2C Shopping Review 1" | weakness=0.79 | 20d ago
    Failed: "The pyjama ___ 300,000 dongs" → student: "cost/price", correct: "is"
    Speaking: Q: "What color is the sky?" → "You see seven." [inaccordant]

SPACED-REP LESSONS:
  ...
```

**Output:** Narrative phân tích tiếng Anh — không có JSON, không có bullet list — gồm:
1. Top 3 error patterns nổi bật nhất
2. Phân tích skill gaps chi tiết từng lesson
3. Đánh giá lesson nào cần luyện sâu vs nhắc lại nhẹ
4. Loại câu hỏi phù hợp nhất cho từng điểm yếu

Lưu tại: `output/diagnostic_output.txt`

---

### Bước 4 — Selector Agent (`agents/selector_agent.py`)

**Model:** GPT-4o | **Temperature:** 0 | **Output:** JSON schema (structured output)

**Input:**
- Diagnostic text từ Bước 3 (làm "briefing" từ giáo viên)
- Question pool (~200–300 câu với metadata days_since + weakness_score)

**Ràng buộc chọn:**
- Ít nhất 3 speaking, 4 grammar/fill-blank, 3 vocabulary
- Không trùng skill từ cùng 1 lesson
- Tie-break: fill-blank > multiple-choice > speaking

**`reason` field — cá nhân hóa:**
Mỗi câu phải có reason 1–2 câu cite cụ thể:
- Lỗi thực tế học sinh đã mắc (wrong answer / transcript)
- Thời gian kể từ lần luyện cuối
- Skill gap được chẩn đoán từ diagnostic

**Output schema:**
```json
{
  "question_no": 1,
  "lesson_id": 3968761,
  "lesson_title": "Unit 2C: Shopping - Lesson 5: Review 2",
  "skill_category": "grammar",
  "question_type": "Điền vào chỗ trống",
  "question_text": "The pyjama ___ 300,000 dongs.",
  "correct_answer": "is",
  "difficulty": "medium",
  "reason": "Student answered 'cost'/'price' instead of 'is' — direct subject-verb agreement error recorded in this lesson. Practiced 6 days ago (weakness=0.62), requires immediate reinforcement per diagnostic."
}
```

Lưu tại: `output/homework_assignment.json`

---

## Cách chạy

### Yêu cầu
```bash
# Python 3.10+, uv package manager
uv sync           # hoặc: pip install openai pytest
export OPENAI_API_KEY=sk-...
```

### Chạy lần đầu (tạo dữ liệu tiền xử lý)
```bash
uv run python preprocess.py        # → output/student_context.json
uv run python export_questions.py  # → output/questions_export.json
```

### Chạy pipeline agent
```bash
uv run python agent_pipeline.py
```

**Output mẫu:**
```
Loading data files...
[1/3] Building context (tiering candidates, building question pool)...
      12 candidates | 247 questions in pool
      Tiers: {'critical': 7, 'spaced_rep': 4, 'maintenance': 1}
[2/3] Running diagnostic agent (GPT-4o)...
      Diagnostic saved → output/diagnostic_output.txt (680 chars)
[3/3] Running selector agent (GPT-4o structured output)...
      Done → output/homework_assignment.json (15 questions)

--- Homework Assignment Summary ---
   1. [grammar     ] [medium] The pyjama ___ 300,000 dongs.
   2. [speaking    ] [hard  ] What do you eat?
   ...
```

### Chạy tests
```bash
uv run pytest tests/ -v   # 22 tests
```

---

## Cấu trúc file

```
phase-0-learning-flow/
├── data/                          # Raw exports từ LMS + Digital Teacher
│   ├── lms_practice_result_*.json
│   ├── program_lesson_*.json
│   ├── tutor_lessons_2102555.json
│   └── vh_digital_teacher.*.json
├── agents/
│   ├── context_builder.py         # Tiering + question pool (no LLM)
│   ├── diagnostic_agent.py        # GPT-4o plain text analysis
│   └── selector_agent.py          # GPT-4o structured output
├── tests/
│   ├── test_context_builder.py    # 8 tests
│   ├── test_diagnostic_agent.py   # 6 tests
│   └── test_selector_agent.py     # 8 tests
├── output/
│   ├── student_context.json       # Profile + scored candidates
│   ├── questions_export.json      # Full question bank
│   ├── diagnostic_output.txt      # Intermediate: LLM analysis
│   └── homework_assignment.json   # FINAL: 15 homework questions
├── preprocess.py                  # Tiền xử lý dữ liệu gốc
├── export_questions.py            # Trích xuất câu hỏi
├── agent_pipeline.py              # Entry point
└── docs/
    ├── SYSTEM.md                  # Tài liệu này
    └── plans/
        ├── 2026-04-21-homework-agent-design.md
        └── 2026-04-21-homework-agent-pipeline.md
```

---

## Quan hệ dữ liệu

```
program_lesson_{id}.json
  └── lesson.id → tutor_lessons (id)
              → vh_digital_teacher.learning_sessions (erpLessonId)
  └── section.lms_id → lms_practice_result (practice_id)
                     → lms_practice_result_detail (practice_id)

lms_practice_result.id → lms_practice_result_detail.result_id
vh_digital_teacher.learning_sessions._id → learning_results.sessionId
```

---

## Quyết định thiết kế quan trọng

| Quyết định | Lý do |
|-----------|-------|
| Diagnostic output = plain text | Tránh lỗi JSON parsing; LLM chain-of-thought tự nhiên hơn; Selector đọc như "briefing từ giáo viên" |
| Selector dùng OpenAI json_schema | Đảm bảo valid JSON 100%; temperature=0 cho kết quả deterministic |
| Pre-filter bằng Python (không dùng LLM) | Context LLM ~5–8k tokens thay vì 50–80k; nhanh hơn 10x, rẻ hơn |
| Greedy diversity boost | Tránh 15 câu từ cùng 1 skill; re-compute sau mỗi pick để boost chính xác |
| Không dùng framework (LangChain/CrewAI) | 2 sequential API calls không cần orchestration; dễ debug hơn |
| English cho diagnostic output | GPT-4o reasoning tốt hơn bằng English; Selector đọc như internal briefing |
