#!/usr/bin/env python3
"""
Evaluate homework pipeline quality across 4 dimensions:
  1. Preprocess quality  — student_context.json signal analysis
  2. Constraint compliance — selector rule adherence per model
  3. Signal adherence — did model prioritize the right lessons?
  4. Reason field quality — LLM-as-judge (OpenAI)

Usage:
  python -m scripts.evaluate 2102555                           # full eval
  python -m scripts.evaluate 2102555 --skip-llm                 # automated only (no API cost)
  python -m scripts.evaluate 2102555 --judge-model gpt-4.1      # specify judge model
  python -m scripts.evaluate 2102555 --models gpt-5.4,gpt-4.1   # evaluate subset
"""

from .constraints import evaluate_constraints
from .data import build_question_id_set, load_data
from .llm_judge import evaluate_reasons_llm
from .pipeline import main
from .preprocess_eval import evaluate_preprocess
from .ranking import compute_ranking
from .report import format_markdown, write_report
from .signal import evaluate_signal_adherence

__all__ = [
    "build_question_id_set",
    "compute_ranking",
    "evaluate_constraints",
    "evaluate_preprocess",
    "evaluate_reasons_llm",
    "evaluate_signal_adherence",
    "format_markdown",
    "load_data",
    "main",
    "write_report",
]
