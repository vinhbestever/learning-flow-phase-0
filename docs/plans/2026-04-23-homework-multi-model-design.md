# Homework pipeline: chọn model & nhiều bản theo model

**Status:** Approved (2026-04-23)  
**Context:** Hiện pipeline gắn cứng `gpt-4o` ở diagnostic (streaming) và selector (JSON schema) trong `web/backend/pipeline_ws.py` và `scripts/agent_pipeline.py`. Một học sinh chỉ có một cặp `diagnostic_output.txt` + `homework_assignment.json`.

## Goals

1. Giao diện **Tạo bài tập** cho phép chọn **một** model mỗi lần chạy từ danh sách được phép (OpenAI — các bản GPT cao hơn; Google — Gemini).
2. Giao diện **Kết quả** hiển thị nhiều bản, **mỗi tên model chỉ giữ bản mới nhất** (chạy lại cùng model = ghi đè bản cũ).
3. CLI `scripts/agent_pipeline.py` hỗ trợ `--model` tương ứng.
4. Tương thích ngược với file cũ dưới `output/{student_id}/`.

## Non-goals (YAGNI)

- Chạy nhiều model trong một lần bấm (A/B cùng request).
- Lịch sử đầy đủ mọi lần chạy cùng model.
- Per-user API keys từ UI; chỉ dùng biến môi trường trên server.
- Tự động chạy lại toàn bộ khi thêm model mới.

## Architecture (recommended)

**Hướng A — adapter theo provider (chọn mặc định):**

- Lớp mỏng: `OpenAI` dùng `AsyncOpenAI` / `OpenAI` cho diagnostic + selector; `Google` dùng GenAI SDK với JSON / schema tương đương cho selector.
- Cùng prompt và cùng `HOMEWORK_SCHEMA` (hoặc bản copy tương thích Gemini) để output thống nhất.
- **Hướng B (tùy chọn sau):** LiteLLM hoặc gateway thống nhất — ghi chú thay thế nếu muốn giảm mã provider.

**Tích hợp:**

- `run_pipeline_ws` đọc `model` từ client (xem dưới), validate allowlist, kiểm tra key phù hợp, gọi diagnostic rồi selector cùng id model.
- Khóa toàn pipeline (`_pipeline_lock`) giữ nguyên mặc định; có thể mở rộng theo `student_id` sau.

## Data model & storage

**File mới:** `output/{student_id}/homework_by_model.json`

- Cấu trúc top-level gợi ý:
  - `version`: số schema (ví dụ `1`) để migration sau này.
  - `last_run_model`: id model vừa chạy thành công lần cuối (tiện UI mặc định).
  - `models`: object map `model_id` → `{ "updated_at": "<ISO-8601>", "diagnostic": string, "homework": array }`.
- `model_id` là chuỗi chính thức từ API (ví dụ `gpt-4.1`, `gemini-2.0-flash`), không dùng slug thư mục.

**Tương thích ngược:**

- Nếu tồn tại `homework_assignment.json` + `diagnostic_output.txt` nhưng chưa có dữ liệu trong `homework_by_model.json` (hoặc lần GET đầu), **import** vào key mặc định `gpt-4o` (khớp hành vi cũ) rồi tùy chọn persist sang file mới.
- Ghi tài liệu: không xóa file cũ ngay trong bản đầu; có thể deprecate sau.

## API & WebSocket

- **WebSocket** ` /api/ws/students/{id}/generate`: client gửi `model` qua **một** cơ chế thống nhất (ví dụ message đầu `{"type":"start","model":"gpt-4.1"}`) hoặc query `?model=` — cần chốt khi implement để dễ test.
- **GET** `/api/students/{id}/homework` (hoặc route hiện có): trả về cấu trúc mới: toàn bộ `models` + `last_run_model` + mỗi bản kèm `updated_at`. Frontend chọn bản theo model.

## Configuration & security

- **Allowlist** model hợp lệ: danh sách cố định trong code hoặc file config, không chấp nhận chuỗi tùy ý từ client.
- **Env:** `OPENAI_API_KEY` bắt buộc khi dùng model OpenAI; `GOOGLE_API_KEY` (tên chốt trong code) khi dùng Gemini. Lỗi thiếu key trả qua WebSocket/HTTP rõ ràng.

## Frontend

- **GenerateHomework:** dropdown chọn model (nhãn thân thiện, value = `model_id`), gửi cùng khi bắt đầu pipeline.
- **HomeworkResult:** chọn “phiên bản theo model” (tabs hoặc select); hiển thị `updated_at` từng bản. Model chưa có bản: không hiện hoặc trạng thái “chưa có bản chạy”.

## Error handling

- Model không trong allowlist → từ chối sớm.
- Thiếu key cho provider → thông báo cấu hình.
- Lỗi API provider → hiện như hiện tại qua `type: error`.

## Testing

- Cập nhật/ thêm test mock: gọi API với `model` khác nhau.
- Test migration từ file cũ → map `gpt-4o`.
- (Tùy chọn) test snapshot cấu trúc `homework_by_model.json` sau một run giả lập.

## Open decisions (resolve during implementation)

- Tên chính xác biến env Google; package Python (google-genai vs google-generativeai) theo bản ổn định hiện tại.
- Bộ model allowlist mặc định (danh sách gpt-4.1, gpt-4o, gemini-2.x-flash, v.v.) — cập nhận khi provider đổi tên.
- Cơ chế WebSocket `start` + `model` cụ thể (message vs query) — ưu tiên nhất quán với cách gửi dữ liệu hiện có.

## References

- `web/backend/pipeline_ws.py` — pipeline async.
- `agents/diagnostic_agent.py`, `agents/selector_agent.py` — prompts và OpenAI.
- `web/backend/routers/homework.py` — `get_homework`.
- `web/frontend/src/pages/GenerateHomework.tsx`, `HomeworkResult.tsx`.
