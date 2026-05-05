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
              │  scripts/preprocess/      │  package (Python thuần)
              │  scripts/export_questions/ │
              └─────────────┬─────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                                   ▼
  output/<student_id>/student_context.json     output/<student_id>/questions_export.json
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
          │   Diagnostic Agent         │  OpenAI hoặc Gemini (chọn model)
          │   (plain text output)      │  temp=0.4
          └─────────────┬─────────────┘
                        │
              output/diagnostic_output.txt
              (~600 words phân tích)
                        │
          ┌─────────────▼─────────────┐
          │   Selector Agent           │  Cùng family model | temp=0 | JSON
          │   (structured output)      │
          └─────────────┬─────────────┘
                        │
              output/homework_assignment.json
              output/homework_by_model.json
              (15 câu; theo model_id, ghi đè bản cũ cùng model)
```

### Nhiều model (web + CLI)

- **Allowlist:** `agents/model_config.py` — chỉ các id API được phép (OpenAI: ví dụ `gpt-5.4`, `gpt-4.1`; Google: ví dụ `gemini-2.5-pro`, `gemini-2.5-flash`). Mặc định pipeline: `DEFAULT_HOMEWORK_MODEL` (hiện `gpt-5.4`).
- **API key:** `OPENAI_API_KEY` khi chọn model OpenAI; `GOOGLE_API_KEY` khi chọn Gemini (Google AI Studio / tương thích `google-genai`).
- **File output:** `homework_by_model.json` giữ **một bản mới nhất cho mỗi** `model_id`. Dữ liệu import từ pipeline cũ (chỉ `homework_assignment.json` + `diagnostic_output.txt`) gắn khóa legacy `gpt-4o` khi đọc lần đầu.
- **Web:** WebSocket `/api/ws/students/{id}/generate?model=...`; `GET /api/homework-models` (danh sách chọn); trang kết quả đọc `GET /api/students/{id}/homework` với `models` + `last_run_model`.
- **CLI:** `python -m scripts.agent_pipeline <student_folder> --model <id>` (hoặc `python agent_pipeline.py …`) — chạy từ thư mục gốc repo; `agents` / `web.backend` được resolve qua cwd trên `sys.path`.

---

## Chi tiết từng bước

### Bước 1 — Tiền xử lý dữ liệu (đã có sẵn)

**Package:** `scripts/preprocess/` (`pipeline.py`, `loaders.py`, …) — lệnh: `python -m scripts.preprocess` → `output/<student_id>/student_context.json`

Đường dẫn dữ liệu theo học sinh nằm trong **`scripts.preprocess.config`** (`DATA_DIR`, `STUDENT_ID`, …).

**Package:** `scripts/export_questions/` (`homework.py`, `in_class.py`, …) — lệnh: `python -m scripts.export_questions` → `output/<student_id>/questions_export.json`

Trước khi gọi loader của preprocess, export gán `preprocess.config.DATA_DIR` khớp thư mục `data/<student_id>/`.

Tính toán (preprocess) cho từng bài học:
- `forgetting_score`: Ebbinghaus `1 - e^(-t/S)`, S=1 ngày. Bài > 7 ngày → score ≈ 1.0
- `weakness_score`: tổng hợp có trọng số (bài tập 35% + luyện tập 15% + free speaking 50%)
- `composite_priority_score`: `0.5 × forgetting + 0.5 × weakness`
- `scored_candidates`: top 20 bài theo composite score, kèm failed questions + worst speaking items

Trích xuất (export_questions) toàn bộ câu hỏi từ dữ liệu gốc, phân loại:
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

### Bước 3 — Diagnostic Agent (`agents/diagnostic_agent.py` / `agents/diagnostic_gemini.py`)

**Model:** chọn trong allowlist (mặc định `gpt-5.4` qua OpenAI; hoặc Gemini) | **Temperature:** 0.4 | **Output:** Plain text (~600 words)

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

### Bước 4 — Selector Agent (`agents/selector_agent.py` / `agents/selector_gemini.py`)

**Model:** cùng id với bước 3 (OpenAI `json_schema` hoặc Gemini `response_json_schema`) | **Temperature:** 0 | **Output:** JSON (structured)

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
uv run python -m scripts.preprocess        # → output/<student_id>/student_context.json
uv run python -m scripts.export_questions  # → output/<student_id>/questions_export.json
```

### Chạy pipeline agent
```bash
uv run python -m scripts.agent_pipeline
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
uv run pytest tests/ -v   # ~50 tests
```

---

## Cấu trúc file

```
phase-0-learning-flow/
├── preprocess.py                  # Shim → python -m scripts.preprocess
├── export_questions.py            # Shim → python -m scripts.export_questions
├── agent_pipeline.py              # Shim → scripts.agent_pipeline
├── evaluate.py                    # Shim → python -m scripts.evaluate
├── lms_question_rich.py           # Re-export → scripts.lms_question_rich
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
│   └── <student_id>/              # e.g. 2102555/
│       ├── student_context.json   # Profile + scored candidates
│       ├── questions_export.json # Full question bank per lesson
│       ├── diagnostic_output.txt  # Intermediate: LLM analysis (nếu có)
│       └── homework_assignment.json  # FINAL: 15 homework questions
├── scripts/
│   ├── preprocess/                # Package: tiền xử lý (config, loaders, pipeline, …)
│   ├── export_questions/          # Package: export câu hỏi (bank, homework, in_class, …)
│   ├── evaluate/                  # Package: đánh giá pipeline (metrics, LLM judge, báo cáo)
│   ├── agent_pipeline.py          # Entry point pipeline agent
│   ├── lms_question_rich.py       # Tiện ích HTML/media cho câu LMS
│   └── analyze_pipeline_model_outputs.py
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
