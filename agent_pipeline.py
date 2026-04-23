"""
Entry point for the homework agent pipeline.

Usage:
    export OPENAI_API_KEY=sk-...   # for OpenAI models
    export GOOGLE_API_KEY=...     # for Gemini models
    python agent_pipeline.py [student_id] [--model MODEL_ID]

Prerequisites:
    output/{student_id}/student_context.json   (run preprocess.py first)
    output/{student_id}/questions_export.json  (run export_questions.py first)

Outputs:
    output/{student_id}/homework_assignment.json
    output/{student_id}/homework_by_model.json  (diagnostic + homework theo từng model)
"""

import argparse
import json
import os
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    from agents.model_config import DEFAULT_HOMEWORK_MODEL

    parser = argparse.ArgumentParser(description="Run homework agent pipeline.")
    parser.add_argument(
        "student_id",
        nargs="?",
        type=str,
        default="2102555",
        help="Student folder name under output/ (numeric or e.g. 2111414_newstudent). Default: 2102555",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_HOMEWORK_MODEL,
        help=f"Model id (default: {DEFAULT_HOMEWORK_MODEL})",
    )
    return parser.parse_args()


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    from agents.model_config import get_provider, is_allowed
    from web.backend.config import student_paths
    from web.backend.homework_storage import save_model_result

    args = _parse_args()
    out = f"output/{args.student_id}"
    student_context_path = f"{out}/student_context.json"
    questions_export_path = f"{out}/questions_export.json"
    paths = student_paths(args.student_id)

    model = args.model
    if not is_allowed(model):
        print(f"ERROR: Model not allowlisted: {model!r}")
        sys.exit(1)
    try:
        provider = get_provider(model)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    for path in (student_context_path, questions_export_path):
        if not Path(path).exists():
            print(f"ERROR: {path} not found. Run preprocess.py / export_questions.py first.")
            sys.exit(1)

    if provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)
    if provider == "google" and not os.environ.get("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY environment variable not set.")
        sys.exit(1)

    Path(out).mkdir(parents=True, exist_ok=True)

    print("Loading data files...")
    student_context = load_json(student_context_path)
    questions_export = load_json(questions_export_path)

    from agents.context_builder import build_context

    print("[1/3] Building context (tiering candidates, building question pool)...")
    tiered_candidates, question_pool = build_context(student_context, questions_export)
    if not tiered_candidates:
        print("ERROR: No candidates found. Check that student_context.json has scored_candidates.")
        sys.exit(1)
    if not question_pool:
        print("ERROR: Question pool is empty. Check that questions_export.json has usable questions.")
        sys.exit(1)

    print(f"      {len(tiered_candidates)} candidates | {len(question_pool)} questions in pool")
    tier_counts: dict = {}
    for c in tiered_candidates:
        t = c["signal_type"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
    print(f"      Tiers: {tier_counts}")

    print(f"[2/3] Running diagnostic ({model})...")
    if provider == "openai":
        from agents.diagnostic_agent import run_diagnostic

        diagnostic_text = run_diagnostic(
            student_context["summary"],
            tiered_candidates,
            model=model,
        )
    else:
        from agents.diagnostic_agent import SYSTEM_PROMPT, build_prompt
        from agents.diagnostic_gemini import run_diagnostic_gemini_sync

        prompt = build_prompt(student_context["summary"], tiered_candidates)
        diagnostic_text = run_diagnostic_gemini_sync(
            model=model,
            system_instruction=SYSTEM_PROMPT,
            user_content=prompt,
        )

    print(f"      Diagnostic done ({len(diagnostic_text)} chars) — stored in homework_by_model.json")

    print(f"[3/3] Running selector ({model})...")
    if provider == "openai":
        from agents.selector_agent import run_selector

        homework = run_selector(
            diagnostic_text=diagnostic_text,
            question_pool=question_pool,
            save_path=str(paths["homework"]),
            model=model,
        )
    else:
        from agents.selector_gemini import run_selector_gemini_sync

        homework = run_selector_gemini_sync(
            diagnostic_text=diagnostic_text,
            question_pool=question_pool,
            save_path=str(paths["homework"]),
            model=model,
        )

    save_model_result(
        paths["homework_by_model"],
        model,
        diagnostic_text,
        homework,
    )
    print(f"      Done → {paths['homework']} + {paths['homework_by_model']}")

    print("\n--- Homework Assignment Summary ---")
    for q in homework:
        tag = "[media] " if q.get("requires_media") else ""
        print(
            f"  {q['question_no']:>2}. [{q['skill_category']:<12}] [{q['difficulty']:<6}] "
            f"{tag}{q['question_text'][:60]}"
        )


if __name__ == "__main__":
    main()
