# Homework multi-model implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Cho phép chọn model (OpenAI GPT mới hơn + Gemini) khi chạy pipeline tạo bài tập; lưu tối đa một bản mỗi `model_id` trong `homework_by_model.json`; UI kết quả chuyển bản theo model; CLI `--model`.

**Architecture:** Allowlist `model_id` trên server; tách gọi API theo provider (OpenAI vs Google) với cùng prompt/schema selector; `pipeline_ws` và `agent_pipeline` ghi/đọc `homework_by_model.json` và migration từ `homework_assignment.json` + `diagnostic_output.txt`. Không dùng LiteLLM trừ khi đổi hướng.

**Tech Stack:** Python 3.10+, FastAPI, existing OpenAI SDK, `google-genai` (hoặc gói GenAI ổn định được chốt lúc implement), React/TS frontend, pytest.

**Design ref:** `docs/plans/2026-04-23-homework-multi-model-design.md`

---

### Task 1: Schema + helper đọc/ghi `homework_by_model.json`

**Files:**

- Create: `web/backend/homework_storage.py` (hoặc `agents/persistence/homework_by_model.py` nếu muốn dùng chung CLI+web)
- Modify: `web/backend/config.py` — thêm path `homework_by_model`
- Test: `tests/test_homework_by_model_storage.py`

**Step 1: Write the failing test**

- `test_load_empty_returns_empty_or_migrated` — thư mục tạm không có file → `models` rỗng.
- `test_migrate_from_legacy_files` — có `homework_assignment.json` + `diagnostic_output.txt` → `load` trả về `models["gpt-4o"]` với nội dung đúng (hoặc hàm migration rõ ràng gọi từ test).

**Step 2: Run test — expect FAIL** (`pytest tests/test_homework_by_model_storage.py -v`)

**Step 3: Implement** `load_homework_state(path, legacy_hw, legacy_diag) -> dict` và `save_model_result(path, model_id, diagnostic, homework, last_run_model)`.

**Step 4: Run test — expect PASS**

**Step 5: Commit** `git add ... && git commit -m "feat: homework_by_model storage and legacy migration"`

---

### Task 2: Allowlist + phân loại provider

**Files:**

- Create: `agents/model_config.py` (hoặc `web/backend/model_allowlist.py`)
- Test: `tests/test_model_config.py`

**Step 1: Failing test** — `is_allowed("gpt-4.1")` True nếu trong list; `get_provider("gpt-4.1")` → `"openai"`; `get_provider("gemini-2.0-flash")` → `"google"`; unknown → False / raise.

**Step 2: pytest — FAIL**

**Step 3: Implement** list hằng số (hoặc đọc từ biến env tùy chọn) gồm vài id OpenAI + vài id Gemini.

**Step 4: pytest — PASS**

**Step 5: Commit**

---

### Task 3: Diagnostic — OpenAI (refactor tham số `model`)

**Files:**

- Modify: `agents/diagnostic_agent.py` — hàm gọi API nhận `model: str` (default `gpt-4o` cho tương thích)
- Modify: `web/backend/pipeline_ws.py` — truyền `model` vào
- Test: `tests/test_diagnostic_agent.py` — assert `call_kwargs["model"]` theo tham số

**Step 1:** Sửa test cũ nếu cần; thêm test với `model="gpt-4.1"`.

**Step 2: pytest** diagnostic tests

**Step 3:** Implement tối thiểu (chỉ tham số hóa, không đổi provider)

**Step 4: pytest — PASS**

**Step 5: Commit**

---

### Task 4: Diagnostic — Google Gemini (streaming tương đương)

**Files:**

- Create: `agents/diagnostic_gemini.py` hoặc mở rộng `diagnostic_agent` với `if provider == "google"`
- Modify: `requirements.txt` / `pyproject.toml` nếu có
- Test: mock HTTP/SDK hoặc mock object client

**Step 1:** Test mock: gọi `stream_diagnostic_gemini(model, ...)` tích lũy text giống OpenAI.

**Step 2: pytest — FAIL**

**Step 3:** Dùng SDK chính thức; stream từng chunk → nối chuỗi; cùng `SYSTEM_PROMPT` + `build_prompt` hiện có.

**Step 4: pytest — PASS**

**Step 5: Commit**

---

### Task 5: Selector — tham số `model` OpenAI

**Files:**

- Modify: `agents/selector_agent.py` — `run_selector(..., model: str = "gpt-4o")`
- Test: `tests/test_selector_agent.py` — `model` truyền vào `chat.completions.create`

**Step 1–5:** Tương tự Task 3.

---

### Task 6: Selector — Gemini JSON schema

**Files:**

- Modify or create: `agents/selector_gemini.py` — parse JSON từ response; map lỗi → `ValueError` giống OpenAI
- Test: mock response hợp lệ theo `HOMEWORK_SCHEMA` / cùng shape list 15 câu

**Step 1–5:** TDD tối thiểu; bảo đảm output list cùng shape với OpenAI.

---

### Task 7: Nối pipeline `run_pipeline_ws` + lưu file mới

**Files:**

- Modify: `web/backend/pipeline_ws.py` — parse `model` từ WS (message `start` hoặc query); validate allowlist + env; chọn OpenAI vs Gemini; sau `done` ghi `homework_by_model.json`
- Test: `tests/test_pipeline_ws.py` nếu chưa có — hoặc test tích hợp mỏng với mock `run_*`

**Step 1:** Test: mock toàn bộ LLM, assert `save` được gọi với `model_id` đúng.

**Step 2–5:** Implement, pytest, commit.

---

### Task 8: API `get_homework`

**Files:**

- Modify: `web/backend/routers/homework.py` — đọc `homework_by_model.json` + migration; response JSON mới: `models`, `last_run_model`, giữ tương thích field cũ nếu cần (ví dụ `homework` = bản `last_run_model` để không gãy client cũ) — **chốt:** hoặc breaking change có version field; tài liệu design ưu tiên cấu trúc mới rõ ràng.

**Step 1:** Test client GET với file fixture.

**Step 2–5:** Implement, commit.

---

### Task 9: Frontend `GenerateHomework` — chọn model

**Files:**

- Modify: `web/frontend/src/pages/GenerateHomework.tsx` — state `model`; fetch allowlist từ GET mới (ví dụ `/api/models` hoặc embed trong trang) — nếu chưa có endpoint, dùng hằng số frontend trùng server tạm thời (ghi TODO đồng bộ)
- Create (optional): `web/backend/routers/models.py` — `GET /api/homework-models` trả list `{ id, label, provider }`

**Step 1:** Thủ công trên dev server sau khi backend sẵn; hoặc test E2E nhỏ nếu có.

**Step 2–5:** Gửi `model` khi mở WS; commit.

---

### Task 10: Frontend `HomeworkResult` — chuyển bản theo model

**Files:**

- Modify: `web/frontend/src/pages/HomeworkResult.tsx` — parse `models` từ API; UI select/tabs; hiển thị `updated_at`

**Step 1:** Điều chỉnh type `HomeworkData`

**Step 2–5:** Build, commit.

---

### Task 11: CLI `agent_pipeline.py` — `--model`

**Files:**

- Modify: `agent_pipeline.py` — `argparse` `--model` default `gpt-4o`; gọi cùng lớp pipeline nội bộ hoặc duplicate logic tối thiểu; ghi `homework_by_model.json`

**Test:** `tests/test_agent_pipeline_cli.py` hoặc subprocess với mock

**Step 5:** Commit

---

### Task 12: Tài liệu & dọn dẹp

**Files:**

- Modify: `CLAUDE.md` hoặc `docs/SYSTEM.md` — biến env `GOOGLE_API_KEY`, file mới, hành vi ghi đè theo model

**Step 1:** Cập nhật tối thiểu

**Step 2:** `pytest` toàn repo

**Step 3:** Commit

---

## Execution handoff

Plan complete and saved to `docs/plans/2026-04-23-homework-multi-model.md`. Two execution options:

**1. Subagent-Driven (this session)** — dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — new session with executing-plans, batch execution with checkpoints

**Which approach?**

If Subagent-Driven: use **subagent-driven-development** skill. If Parallel: use **executing-plans** in a worktree per brainstorming.
