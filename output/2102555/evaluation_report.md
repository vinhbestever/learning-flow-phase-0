# Pipeline Quality Evaluation — Student 2102555
_Evaluated: 2026-05-04T08:27:06 UTC_

---

## 1. Preprocess Quality

**Candidates:** 40 total | Critical: 28 | Spaced-rep: 12 | Maintenance: 0

**Score distribution (composite_priority_score):**
mean=0.7645 ± 0.0506 | range [0.6375, 1.0] | p25/median/p75 = 0.75 / 0.7588 / 0.7675

**Signal coverage across candidates:**
- Failed text questions: 35%
- Speaking failures: 100%
- Question bank preview: 2%
- No-signal candidates: 0

**Speaking averages:**
- Brainstorm: **15.85/100** ⚠️ CRITICAL
- Free speaking: 57.78/100
- Pronunciation: 86.96/100
- Conversation: 86.26/100
- `weak_skills_global` empty: **True** ← speaking crisis not visible here

**Forgetting ceiling:** 31 / 40 candidates (78%) at forgetting_score≈1.0 (stability=7d)

_No issues found._

---

## 2. Model Ranking

Scoring weights: Constraint 25% | Signal 35% | Reason quality 25% | Diagnostic 15%
_(When LLM judge unavailable: Constraint 40% | Signal 60%)_

| Model | Overall | Tier | Constraint | Signal | Reason/5 | Diagnostic/5 |
|-------|---------|------|------------|--------|----------|--------------|
| gpt-5.4 | **88.5** | A | 100.0 | 75.6 | 4.56 | 4.75 |
| gemini-2.5-pro | **85.6** | A | 100.0 | 71.1 | 4.6 | 4.25 |
| gemini-3.1-pro-preview | **84.6** | A | 100.0 | 74.0 | 4.2 | 4.25 |
| gpt-5.4-mini | **83.7** | A | 100.0 | 63.4 | 4.44 | 4.75 |
| gpt-4.1 | **83.0** | A | 100.0 | 70.3 | 4.28 | 4 |
| gemini-2.5-flash | **82.0** | A | 100.0 | 73.9 | 4.12 | 3.5 |
| gpt-4.1-mini | **81.5** | A | 100.0 | 72.4 | 3.68 | 4.25 |
| gpt-5.4-nano | **78.7** | B | 100.0 | 73.1 | 2.92 | 4.5 |
| gemini-2.5-flash-lite | **76.8** | B | 100.0 | 73.1 | 2.84 | 4 |
| gpt-4.1-nano | **70.6** | B | 100.0 | 73.1 | 2.36 | 2.75 |

---

## 3. Constraint Compliance

| Model | Score | 15q | spk≥3 | grm≥4 | voc≥3 | ≤2/less | diff_skill | media≤4 | VN reason | valid IDs |
|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| gemini-2.5-flash | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gemini-2.5-flash-lite | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gemini-2.5-pro | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gemini-3.1-pro-preview | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gpt-4.1 | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gpt-4.1-mini | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gpt-4.1-nano | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gpt-5.4 | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gpt-5.4-mini | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gpt-5.4-nano | 1.00 (9/9) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 4. Signal Adherence

| Model | Score | Avg Priority | Critical% | Top3 | NA cov. | Speaking | Old5 | Tier dist (c/s/m) |
|-------|-------|-------------|-----------|------|---------|----------|------|--------------------|
| gemini-2.5-flash | 0.739 | 0.799 | 36% | 3/3 | 100% | 5✓(≥5) | 3/5 | 12/3/0 |
| gemini-2.5-flash-lite | 0.731 | 0.803 | 32% | 3/3 | 100% | 5✓(≥5) | 3/5 | 13/2/0 |
| gemini-2.5-pro | 0.711 | 0.803 | 32% | 3/3 | 100% | 5✓(≥5) | 2/5 | 11/4/0 |
| gemini-3.1-pro-preview | 0.740 | 0.801 | 36% | 3/3 | 100% | 5✓(≥5) | 3/5 | 12/3/0 |
| gpt-4.1 | 0.704 | 0.807 | 29% | 3/3 | 100% | 5✓(≥5) | 2/5 | 13/2/0 |
| gpt-4.1-mini | 0.724 | 0.807 | 29% | 3/3 | 100% | 5✓(≥5) | 3/5 | 11/4/0 |
| gpt-4.1-nano | 0.731 | 0.803 | 32% | 3/3 | 100% | 5✓(≥5) | 3/5 | 12/3/0 |
| gpt-5.4 | 0.756 | 0.796 | 43% | 3/3 | 100% | 5✓(≥5) | 3/5 | 12/3/0 |
| gpt-5.4-mini | 0.634 | 0.799 | 29% | 2/3 | 100% | 6✓(≥5) | 2/5 | 14/1/0 |
| gpt-5.4-nano | 0.731 | 0.803 | 32% | 3/3 | 100% | 5✓(≥5) | 3/5 | 12/3/0 |

---

## 5. LLM-as-Judge (Reason & Diagnostic Quality)

| Model | Reason avg | Specificity | Timing | Accuracy | Actionability | Language | Diagnostic |
|-------|-----------|------------|--------|----------|--------------|----------|------------|
| gemini-2.5-flash | 4.12 | 2.6 | 5 | 4.6 | 3.4 | 5 | 3.5 |
| gemini-2.5-flash-lite | 2.84 | 2 | 2.6 | 3.2 | 2 | 4.4 | 4 |
| gemini-2.5-pro | 4.6 | 4.2 | 5 | 5 | 3.8 | 5 | 4.25 |
| gemini-3.1-pro-preview | 4.2 | 3 | 5 | 4.6 | 3.4 | 5 | 4.25 |
| gpt-4.1 | 4.28 | 3 | 5 | 4.8 | 3.6 | 5 | 4 |
| gpt-4.1-mini | 3.68 | 2.2 | 4.2 | 4.4 | 2.8 | 4.8 | 4.25 |
| gpt-4.1-nano | 2.36 | 1.2 | 1.8 | 3.2 | 1.4 | 4.2 | 2.75 |
| gpt-5.4 | 4.56 | 4 | 5 | 4.4 | 4.4 | 5 | 4.75 |
| gpt-5.4-mini | 4.44 | 3.6 | 5 | 4.4 | 4.2 | 5 | 4.75 |
| gpt-5.4-nano | 2.92 | 1.8 | 2.6 | 3.6 | 2.2 | 4.4 | 4.5 |

---

## 6. Improvement Suggestions

- No critical issues detected. Pipeline is operating within defined constraints.
