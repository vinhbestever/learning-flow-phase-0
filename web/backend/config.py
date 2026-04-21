from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent

STUDENT_CONTEXT_PATH = _ROOT / "output" / "student_context.json"
QUESTIONS_EXPORT_PATH = _ROOT / "output" / "questions_export.json"
HOMEWORK_PATH = _ROOT / "output" / "homework_assignment.json"
DIAGNOSTIC_PATH = _ROOT / "output" / "diagnostic_output.txt"
