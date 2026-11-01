"""
run_eval.py — Automated evaluation runner for LexAid RAG pipeline.

Usage:
    python evaluation/run_eval.py                     # run all 130 questions
    python evaluation/run_eval.py --limit 20          # run first 20
    python evaluation/run_eval.py --category criminal # run one category
    python evaluation/run_eval.py --ids 1,5,23        # run specific IDs

Output:
    evaluation/results_<timestamp>.json   — full per-question results
    evaluation/report_<timestamp>.txt     — human-readable summary
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

API_BASE = "http://localhost:8000"
EVAL_FILE = Path(__file__).parent / "eval_set.json"

# ── Scoring ──────────────────────────────────────────────────────────────────

def score_answer(answer: str, entry: dict) -> dict:
    """Returns per-question score breakdown."""
    answer_lower = answer.lower()

    # 1. Act mentioned (any expected act short name or full name in the answer)
    act_hit = any(
        act.lower() in answer_lower
        for act in entry["expected_acts"]
    )

    # 2. Key terms found (how many of the key_terms appear in the answer)
    terms_found = [t for t in entry["key_terms"] if t.lower() in answer_lower]
    term_ratio = len(terms_found) / len(entry["key_terms"]) if entry["key_terms"] else 1.0

    # 3. Section cited (if section given, check if it appears)
    section = entry.get("section", "")
    section_hit = (not section) or (section.lower() in answer_lower)

    # 4. Disclaimer present
    disclaimer_hit = "not legal advice" in answer_lower or "legal information" in answer_lower

    # Composite score (weighted)
    score = (
        0.35 * float(act_hit) +
        0.35 * term_ratio +
        0.20 * float(section_hit) +
        0.10 * float(disclaimer_hit)
    )

    return {
        "act_hit":      act_hit,
        "terms_found":  terms_found,
        "terms_total":  len(entry["key_terms"]),
        "term_ratio":   round(term_ratio, 2),
        "section_hit":  section_hit,
        "disclaimer":   disclaimer_hit,
        "score":        round(score, 3),
    }


# ── API call ─────────────────────────────────────────────────────────────────

def ask(question: str, category: str) -> tuple[str, list[str], float]:
    """Returns (answer_text, sources, elapsed_seconds)."""
    t0 = time.time()
    try:
        res = requests.post(
            f"{API_BASE}/api/query",
            json={"question": question, "category": category, "language": "en"},
            stream=True,
            timeout=60,
        )
        res.raise_for_status()
    except Exception as e:
        return f"[REQUEST ERROR: {e}]", [], 0.0

    answer = ""
    sources = []
    for raw in res.iter_lines(decode_unicode=True):
        if not raw.startswith("data: "):
            continue
        try:
            evt = json.loads(raw[6:])
        except json.JSONDecodeError:
            continue
        if evt.get("type") == "token":
            answer += evt.get("text", "")
        elif evt.get("type") == "sources":
            sources = evt.get("sources", [])
        elif evt.get("type") == "error":
            answer += f"[ERROR: {evt.get('message')}]"

    return answer, sources, round(time.time() - t0, 2)


# ── Runner ────────────────────────────────────────────────────────────────────

def run(entries: list[dict], verbose: bool = True) -> list[dict]:
    results = []
    for i, entry in enumerate(entries, 1):
        qid = entry["id"]
        q   = entry["question"]
        cat = entry["category"]

        if verbose:
            print(f"[{i:3}/{len(entries)}] Q{qid}: {q[:70]}…")

        answer, sources, elapsed = ask(q, cat)
        breakdown = score_answer(answer, entry)

        result = {
            "id":        qid,
            "question":  q,
            "category":  cat,
            "expected_acts": entry["expected_acts"],
            "sources_returned": sources,
            "answer_snippet": answer[:300],
            "elapsed_s": elapsed,
            **breakdown,
        }
        results.append(result)

        emoji = "✅" if breakdown["score"] >= 0.6 else ("⚠️ " if breakdown["score"] >= 0.35 else "❌")
        if verbose:
            print(f"     {emoji} score={breakdown['score']:.2f}  "
                  f"act={'✓' if breakdown['act_hit'] else '✗'}  "
                  f"terms={len(breakdown['terms_found'])}/{breakdown['terms_total']}  "
                  f"section={'✓' if breakdown['section_hit'] else '✗'}  "
                  f"({elapsed}s)")

    return results


# ── Report ────────────────────────────────────────────────────────────────────

def write_report(results: list[dict], out_dir: Path) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save JSON
    json_path = out_dir / f"results_{ts}.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Aggregate stats
    total       = len(results)
    avg_score   = sum(r["score"] for r in results) / total
    pass_60     = sum(1 for r in results if r["score"] >= 0.60)
    pass_35     = sum(1 for r in results if r["score"] >= 0.35)
    act_hits    = sum(1 for r in results if r["act_hit"])
    section_hits= sum(1 for r in results if r["section_hit"])
    avg_elapsed = sum(r["elapsed_s"] for r in results) / total

    # Per-category breakdown
    cats: dict[str, list] = {}
    for r in results:
        cats.setdefault(r["category"], []).append(r["score"])

    lines = [
        "=" * 62,
        "LexAid Evaluation Report",
        f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Questions evaluated: {total}",
        "=" * 62,
        "",
        "Overall",
        "-" * 40,
        f"  Average score      : {avg_score:.3f} / 1.000",
        f"  Pass (≥0.60)       : {pass_60}/{total}  ({100*pass_60/total:.1f}%)",
        f"  Marginal (≥0.35)   : {pass_35}/{total}  ({100*pass_35/total:.1f}%)",
        f"  Act correctly cited: {act_hits}/{total}  ({100*act_hits/total:.1f}%)",
        f"  Section cited      : {section_hits}/{total}  ({100*section_hits/total:.1f}%)",
        f"  Avg response time  : {avg_elapsed:.1f}s",
        "",
        "By category",
        "-" * 40,
    ]
    for cat, scores in sorted(cats.items()):
        avg = sum(scores) / len(scores)
        lines.append(f"  {cat:<18}: {avg:.3f}  (n={len(scores)})")

    lines += [
        "",
        "Lowest scoring questions (need improvement)",
        "-" * 40,
    ]
    worst = sorted(results, key=lambda r: r["score"])[:10]
    for r in worst:
        lines.append(f"  Q{r['id']:3} score={r['score']:.2f}: {r['question'][:60]}")

    lines += ["", "=" * 62]
    report = "\n".join(lines)

    txt_path = out_dir / f"report_{ts}.txt"
    txt_path.write_text(report, encoding="utf-8")

    print("\n" + report)
    print(f"\nSaved: {json_path}")
    print(f"Saved: {txt_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="LexAid evaluation runner")
    parser.add_argument("--limit",    type=int,   default=0,  help="Run only first N questions")
    parser.add_argument("--category", type=str,   default="", help="Filter by category")
    parser.add_argument("--ids",      type=str,   default="", help="Comma-separated question IDs")
    parser.add_argument("--quiet",    action="store_true",    help="Suppress per-question output")
    args = parser.parse_args()

    # Check API health
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        r.raise_for_status()
        print(f"✅ Backend healthy: {r.json()}\n")
    except Exception as e:
        print(f"❌ Backend not reachable at {API_BASE}: {e}")
        print("   Start it with: .venv\\Scripts\\uvicorn.exe main:app --port 8000")
        sys.exit(1)

    entries = json.loads(EVAL_FILE.read_text(encoding="utf-8"))

    # Filters
    if args.ids:
        id_set = {int(x.strip()) for x in args.ids.split(",")}
        entries = [e for e in entries if e["id"] in id_set]
    if args.category:
        entries = [e for e in entries if e["category"] == args.category]
    if args.limit:
        entries = entries[:args.limit]

    print(f"Running {len(entries)} questions…\n")
    results = run(entries, verbose=not args.quiet)
    write_report(results, EVAL_FILE.parent)


if __name__ == "__main__":
    main()
