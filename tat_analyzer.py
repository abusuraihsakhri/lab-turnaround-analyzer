#!/usr/bin/env python3
"""
Lab Turnaround Time Analyzer
TAT percentiles, breach rates and outlier detection from lab LIS timestamps.
Stdlib parser / mapper with batch CSV and single lookup.
"""
import argparse
import csv
import sys
import re
import json
import pathlib
import os

# Built-in reference dictionaries per domain slug
LOOKUP_BANK = {
    "loinc-lab-mapper": [
        ("2160-0 Creatinine", "creatinine"),
        ("6690-2 WBC", "wbc"),
        ("718-7 Hemoglobin", "hemoglobin"),
        ("4548-4 HbA1c", "hba1c"),
    ],
    "hla-compatibility-matcher": [
        ("A*02:01", "A02"),
        ("B*07:02", "B07"),
        ("DRB1*15:01", "DRB115"),
    ],
    "icd10-ccsr-mapper": [
        ("I10 Hypertension", "I10"),
        ("E11 Type 2 diabetes", "E11"),
        ("J18 Pneumonia", "J18"),
    ],
    "antibiogram-mdr-classifier": [
        ("MDR", "multidrug"),
        ("XDR", "extensive"),
        ("PDR", "pandrug"),
    ],
    "fhir-bundle-validator": [
        ("Patient", "patient"),
        ("Observation", "observation"),
    ],
    "cyp-drug-interaction-checker": [
        ("CYP3A4 substrate", "cyp3a4"),
        ("CYP2D6 inhibitor", "cyp2d6"),
    ],
    "lab-turnaround-analyzer": [
        ("Creatinine", "creatinine"),
        ("Hemoglobin", "hemoglobin"),
        ("WBC", "wbc"),
        ("HbA1c", "hba1c"),
        ("Platelets", "platelets"),
    ],
}


def lookup(query, extra=None):
    """Single lookup: token overlap + substring scoring (no deps). Returns top hits.

    Args:
        query: The search term to look up.
        extra: Optional dictionary with additional candidates or a slug string to select
               a specific reference dictionary from LOOKUP_BANK.
    """
    q = str(query).lower().strip()

    # Build candidate list from bank selection and/or extra parameter
    candidates = list(LOOKUP_BANK.get("lab-turnaround-analyzer", []))
    if isinstance(extra, dict) and "candidates" in extra:
        candidates.extend(extra["candidates"])
    elif isinstance(extra, str) and extra in LOOKUP_BANK:
        candidates = list(LOOKUP_BANK[extra])

    scored = []
    for label, key in candidates:
        score = 0
        # Case-insensitive key matching against lowercased query
        if key and key.lower() in q:
            score += 10
        # token overlap
        qt = set(q.split())
        lt = set(label.lower().split())
        overlap = len(qt & lt)
        score += overlap * 2
        scored.append((score, label))
    scored.sort(reverse=True)
    top = scored[0] if scored else (0, "no match")
    return {"query": query, "top_hit": top[1], "score": top[0], "all": scored[:3]}


def _safe_path(filepath, must_exist=False):
    """Validate a file path to prevent path traversal attacks.

    Returns the resolved absolute path if valid.
    Raises ValueError if path traversal is detected or path doesn't exist when required.
    """
    resolved = pathlib.Path(filepath).resolve()
    cwd = pathlib.Path.cwd().resolve()

    # Allow paths under cwd or in temp directories (for test outputs)
    temp_dir = pathlib.Path(os.environ.get("TEMP", "/tmp")).resolve()
    if not (resolved.is_relative_to(cwd) or resolved.is_relative_to(temp_dir)):
        raise ValueError(
            f"Path traversal blocked: '{filepath}' resolves outside the working directory"
        )

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Input file not found: '{filepath}'")

    return resolved


def process_csv(inp, out):
    """Process a CSV file, performing lookups on each row.

    Args:
        inp: Path to input CSV file.
        out: Path to output CSV file.

    Returns:
        List of result dictionaries.

    Raises:
        ValueError: If a path traversal attempt is detected.
        FileNotFoundError: If the input file does not exist.
    """
    inp_path = _safe_path(inp, must_exist=True)
    out_path = _safe_path(out, must_exist=False)

    with open(inp_path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fn = r.fieldnames or []
        # guess query column
        qcol = fn[0] if fn else ""
        for cand in ["query", "test", "drug", "code", "variant", "hla", "lab", "name"]:
            if cand in [c.lower() for c in fn]:
                qcol = [c for c in fn if c.lower() == cand][0]
                break
        results = []
        for row in rows:
            res = lookup(row.get(qcol, ""), row)
            merged = {**row, "top_hit": res["top_hit"], "lookup_score": res["score"]}
            results.append(merged)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fn) + ["top_hit", "lookup_score"])
        w.writeheader()
        w.writerows(results)
    return results

def build_parser():
    p=argparse.ArgumentParser(prog="tat_analyzer", description="Lab Turnaround Time Analyzer")
    sub=p.add_subparsers(dest="cmd", required=True)
    s=sub.add_parser("single"); s.add_argument("query", nargs="?", default="creatinine"); s.add_argument("--query", dest="q2")
    b=sub.add_parser("batch"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
    a=sub.add_parser("analyze", help="Analyze timezone-aware LIS timestamps")
    a.add_argument("--input", required=True, help="CSV with test, received_at, reported_at")
    a.add_argument("--threshold-minutes", type=float, default=60)
    a.add_argument("--output", help="Optional annotated CSV destination")
    a.add_argument("--report", help="Optional summary JSON destination")
    return p

def main(argv=None):
    p=build_parser(); a=p.parse_args(argv)
    if a.cmd=="single":
        q=getattr(a,"q2",None) or getattr(a,"query")
        print(lookup(q)); return 0
    if a.cmd=="analyze":
        from tat_metrics import analyze_csv, annotated_csv
        with open(a.input, encoding="utf-8-sig", newline="") as source:
            result = analyze_csv(source.read(), a.threshold_minutes)
        summary = {k: result[k] for k in ("threshold_minutes", "overall", "by_test")}
        if a.output:
            with open(a.output, "w", encoding="utf-8", newline="") as target:
                target.write(annotated_csv(result))
        if a.report:
            with open(a.report, "w", encoding="utf-8") as target:
                json.dump(summary, target, indent=2)
        print(json.dumps(summary, indent=2))
        return 0
    if a.cmd=="batch":
        res=process_csv(a.input, a.output); print(f"Processed {len(res)} -> {a.output}"); return 0
    p.print_help(); return 1

if __name__=="__main__":
    import sys; sys.exit(main())
