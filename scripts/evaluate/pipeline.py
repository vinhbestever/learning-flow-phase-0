from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

from .constraints import evaluate_constraints
from .data import load_data
from .llm_judge import evaluate_reasons_llm
from .preprocess_eval import evaluate_preprocess
from .ranking import compute_ranking
from .report import _fmt, write_report
from .signal import evaluate_signal_adherence


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate homework pipeline quality")
    parser.add_argument("student_id", help="Student ID (e.g. 2102555)")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM-as-judge (no API calls)")
    parser.add_argument("--judge-model", default="gpt-4.1", help="OpenAI model to use as judge")
    parser.add_argument("--models", default=None, help="Comma-separated models to evaluate (default: all)")
    args = parser.parse_args()

    print(f"\nLoading data for student {args.student_id}...")
    student_context, homework_by_model, _questions_export = load_data(args.student_id)

    cand_map = {c["lesson_id"]: c for c in student_context["scored_candidates"]}

    all_models = list(homework_by_model["models"].keys())
    models_to_eval = [m.strip() for m in args.models.split(",")] if args.models else all_models
    print(f"Models: {models_to_eval}")

    print("\n[1/4] Preprocess quality...")
    prep = evaluate_preprocess(student_context)
    print(f"  Candidates: {prep['tier_breakdown']['total']} | Issues: {prep['issue_count']}")

    print("\n[2/4] Constraint compliance...")
    constraint_results: dict[str, dict] = {}
    for model in models_to_eval:
        hw = homework_by_model["models"][model].get("homework", [])
        constraint_results[model] = evaluate_constraints(hw, cand_map)
        cr = constraint_results[model]
        print(f"  {model:<30} {cr['score']:.2f} ({cr['passed']}/{cr['total']}) — {cr['skill_distribution']}")

    print("\n[3/4] Signal adherence...")
    signal_results: dict[str, dict] = {}
    for model in models_to_eval:
        hw = homework_by_model["models"][model].get("homework", [])
        signal_results[model] = evaluate_signal_adherence(hw, student_context)
        sr = signal_results[model]
        print(
            f"  {model:<30} score={sr['score']:.3f} "
            f"| priority={sr['avg_priority_score_selected']:.3f} "
            f"| critical={sr['critical_tier_coverage']:.0%} "
            f"| speaking={sr['speaking_count']}{'✓' if sr['brainstorm_emphasis_ok'] else '✗'}"
        )

    llm_results: dict | None = None
    if not args.skip_llm:
        if os.environ.get("OPENAI_API_KEY"):
            print(f"\n[4/4] LLM-as-Judge with {args.judge_model}...")
            try:
                random.seed(42)
                llm_results = evaluate_reasons_llm(
                    homework_by_model, student_context, args.judge_model, models_to_eval
                )
            except Exception as exc:
                print(f"  LLM judge failed: {exc}")
        else:
            print("\n[4/4] Skipping LLM judge — OPENAI_API_KEY not set")
    else:
        print("\n[4/4] Skipping LLM judge (--skip-llm)")

    ranking = compute_ranking(constraint_results, signal_results, llm_results)

    output_dir = Path("output") / args.student_id
    json_path, md_path = write_report(
        args.student_id, prep, constraint_results, signal_results, llm_results, ranking, output_dir
    )

    print("\nReports saved:")
    print(f"  {json_path}")
    print(f"  {md_path}")

    print("\n=== Model Ranking ===")
    hdr = f"{'Model':<30} {'Overall':>8} {'Tier':>4} {'Constraint':>11} {'Signal':>7}"
    if llm_results:
        hdr += f" {'Reason':>7} {'Diag':>5}"
    print(hdr)
    print("—" * len(hdr))
    for r in ranking:
        row = (
            f"{r['model']:<30} {r['overall_score']:>8.1f} {r['tier']:>4} "
            f"{r['constraint_score']:>11.1f} {r['signal_score']:>7.1f}"
        )
        if llm_results:
            row += f" {_fmt(r['reason_score']):>7} {_fmt(r['diagnostic_score']):>5}"
        print(row)

    if prep["issues"]:
        print(f"\n=== Preprocess Issues ({prep['issue_count']}) ===")
        for issue in prep["issues"]:
            print(f"  • {issue[:120]}")


if __name__ == "__main__":
    main()
