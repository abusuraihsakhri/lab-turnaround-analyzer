"""Timezone-aware laboratory turnaround time (TAT) analysis.

TAT = reported_at minus received_at in elapsed minutes. Percentiles use
linear interpolation at (n-1)*p. Breaches are strictly greater than target.
Upper Tukey IQR outliers require at least four samples of the same test.
"""
import csv
import io
import math
from datetime import datetime

REQUIRED_COLUMNS = ("test", "received_at", "reported_at")
MAX_RECORDS = 20000
MAX_CSV_CHARS = 2_000_000


def _timestamp(value, row_number, column):
    try:
        dt = datetime.fromisoformat((value or "").strip().replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number}: invalid {column} timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"Row {row_number}: {column} must include UTC offset or Z")
    return dt


def _quantile(values, p):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _summary(records, target):
    values = [row["tat_minutes"] for row in records]
    breached = sum(value > target for value in values)
    return {
        "count": len(values),
        "mean_minutes": round(sum(values) / len(values), 3),
        "p50_minutes": round(_quantile(values, 0.50), 3),
        "p90_minutes": round(_quantile(values, 0.90), 3),
        "p95_minutes": round(_quantile(values, 0.95), 3),
        "max_minutes": round(max(values), 3),
        "breach_count": breached,
        "breach_rate_pct": round(100 * breached / len(values), 3),
        "outlier_count": sum(row["outlier"] for row in records),
    }


def analyze_csv(csv_text, threshold_minutes=60):
    """Calculate overall and test-stratified metrics; reject malformed input."""
    target = float(threshold_minutes)
    if not math.isfinite(target) or target <= 0:
        raise ValueError("Threshold must be positive and finite, in minutes")
    if len(csv_text) > MAX_CSV_CHARS:
        raise ValueError("CSV exceeds 2,000,000 characters")

    reader = csv.DictReader(io.StringIO(csv_text, newline=""), strict=True)
    fields = reader.fieldnames
    if not fields:
        raise ValueError("CSV is missing a header")
    fields = [field.lstrip("\ufeff").strip() for field in fields]
    if any(not field for field in fields) or len(set(fields)) != len(fields):
        raise ValueError("CSV has empty or duplicate column names")
    reader.fieldnames = fields
    missing = set(REQUIRED_COLUMNS).difference(fields)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))

    records, groups = [], {}
    try:
        for line, row in enumerate(reader, start=2):
            if len(records) >= MAX_RECORDS:
                raise ValueError("CSV exceeds 20,000 records")
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Row {line}: column count does not match header")
            test = row["test"].strip()
            if not test:
                raise ValueError(f"Row {line}: test cannot be empty")
            start = _timestamp(row["received_at"], line, "received_at")
            end = _timestamp(row["reported_at"], line, "reported_at")
            minutes = (end - start).total_seconds() / 60
            if minutes < 0:
                raise ValueError(f"Row {line}: reported_at precedes received_at")
            annotated = {**row, "test": test, "tat_minutes": round(minutes, 6),
                         "breached": minutes > target, "outlier": False}
            records.append(annotated)
            groups.setdefault(test, []).append(annotated)
    except csv.Error as exc:
        raise ValueError(f"Invalid CSV format: {exc}") from exc
    if not records:
        raise ValueError("CSV contains no data rows")

    for group in groups.values():
        if len(group) < 4:
            continue
        values = [record["tat_minutes"] for record in group]
        q1, q3 = _quantile(values, 0.25), _quantile(values, 0.75)
        upper_fence = q3 + 1.5 * (q3 - q1)
        for record in group:
            record["outlier"] = record["tat_minutes"] > upper_fence

    return {"threshold_minutes": target, "overall": _summary(records, target),
            "by_test": {name: _summary(group, target) for name, group in sorted(groups.items())},
            "records": records, "input_columns": fields}


def annotated_csv(result):
    """Return annotated CSV, neutralizing spreadsheet-formula injection."""
    out = io.StringIO(newline="")
    fields = [key for key in result["input_columns"]
              if key not in ("tat_minutes", "breached", "outlier")]
    fields += ["tat_minutes", "breached", "outlier"]
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writerow({field: "'" + field if field.lstrip().startswith(
        ("=", "+", "-", "@", "\t", "\r")) else field for field in fields})
    for record in result["records"]:
        safe = dict(record)
        for field in result["input_columns"]:
            value = str(safe.get(field, ""))
            if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                safe[field] = "'" + value
        writer.writerow(safe)
    return out.getvalue()
