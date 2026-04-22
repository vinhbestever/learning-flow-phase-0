"""
Entry point for the homework agent pipeline.

Usage:
    export OPENAI_API_KEY=sk-...
    python agent_pipeline.py [student_id]

Prerequisites:
    output/{student_id}/student_context.json   (run preprocess.py first)
    output/{student_id}/questions_export.json  (run export_questions.py first)

Outputs:
    output/{student_id}/diagnostic_output.txt
    output/{student_id}/homework_assignment.json
"""

import argparse
import json
import os
import sys
from pathlib import Path


def _parse_args():
    parser = argparse.ArgumentParser(description="Run homework agent pipeline.")
    parser.add_argument(
        "student_id", nargs="?", type=int, default=2102555,
        help="Student ID. Default: 2102555",
    )
    return parser.parse_args()


_args = _parse_args()
_out = f"output/{_args.student_id}"

STUDENT_CONTEXT_PATH = f"{_out}/student_context.json"
QUESTIONS_EXPORT_PATH = f"{_out}/questions_export.json"
DIAGNOSTIC_OUTPUT = f"{_out}/diagnostic_output.txt"
HOMEWORK_OUTPUT = f"{_out}/homework_assignment.json"


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    # Validate prerequisites
    for path in (STUDENT_CONTEXT_PATH, QUESTIONS_EXPORT_PATH):
        if not Path(path).exists():
            print(f"ERROR: {path} not found. Run preprocess.py / export_questions.py first.")
            sys.exit(1)
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    Path(_out).mkdir(parents=True, exist_ok=True)

    print("Loading data files...")
    student_context = load_json(STUDENT_CONTEXT_PATH)
    questions_export = load_json(QUESTIONS_EXPORT_PATH)

    # Step 1: Build context
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
    tier_counts = {}
    for c in tiered_candidates:
        t = c["signal_type"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
    print(f"      Tiers: {tier_counts}")

    # Step 2: Diagnostic agent
    from agents.diagnostic_agent import run_diagnostic

    print("[2/3] Running diagnostic agent (GPT-4o)...")
    diagnostic_text = run_diagnostic(
        summary=student_context["summary"],
        candidates=tiered_candidates,
        save_path=DIAGNOSTIC_OUTPUT,
    )
    print(f"      Diagnostic saved → {DIAGNOSTIC_OUTPUT} ({len(diagnostic_text)} chars)")

    # Step 3: Selector agent
    from agents.selector_agent import run_selector

    print("[3/3] Running selector agent (GPT-4o structured output)...")
    homework = run_selector(
        diagnostic_text=diagnostic_text,
        question_pool=question_pool,
        save_path=HOMEWORK_OUTPUT,
    )
    print(f"      Done → {HOMEWORK_OUTPUT} ({len(homework)} questions)")

    # Summary
    print("\n--- Homework Assignment Summary ---")
    for q in homework:
        tag = "[media] " if q.get("requires_media") else ""
        print(
            f"  {q['question_no']:>2}. [{q['skill_category']:<12}] [{q['difficulty']:<6}] "
            f"{tag}{q['question_text'][:60]}"
        )


if __name__ == "__main__":
    main()
