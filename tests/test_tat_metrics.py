"""Regression tests for timestamp TAT analysis."""
import pytest
from tat_metrics import analyze_csv, annotated_csv

CSV = (
    "test,received_at,reported_at,specimen_id\n"
    "CBC,2026-10-01T08:00:00Z,2026-10-01T08:30:00Z,1\n"
    "CBC,2026-10-01T08:00:00+00:00,2026-10-01T09:00:00Z,2\n"
    "CBC,2026-10-01T08:00:00Z,2026-10-01T09:30:00Z,3\n"
    "CBC,2026-10-01T08:00:00Z,2026-10-01T12:00:00Z,4\n"
    "CRP,2026-10-01T10:00:00+02:00,2026-10-01T09:20:00Z,5\n"
)


def test_statistics_and_offsets():
    result = analyze_csv(CSV, 60)
    assert result["overall"]["count"] == 5
    assert result["overall"]["breach_count"] == 3
    assert result["overall"]["breach_rate_pct"] == 60
    assert result["by_test"]["CBC"]["p50_minutes"] == 75
    assert result["by_test"]["CBC"]["p90_minutes"] == 195
    assert result["by_test"]["CRP"]["mean_minutes"] == 80


def test_iqr_outlier():
    rows = ["test,received_at,reported_at"]
    for mins in (10, 10, 10, 10, 100):
        rows.append(f"X,2026-01-01T00:00:00Z,2026-01-01T{mins//60:02d}:{mins%60:02d}:00Z")
    result = analyze_csv("\n".join(rows))
    assert result["overall"]["outlier_count"] == 1
    assert result["records"][-1]["outlier"] is True


@pytest.mark.parametrize("text,part", [
    ("test,received_at,reported_at\nA,2026-01-01T00:00:00Z,2025-12-31T23:00:00Z", "precedes"),
    ("test,received_at,reported_at\nA,2026-01-01T00:00:00,2026-01-01T01:00:00Z", "offset"),
    ("test,received_at,reported_at\nA,invalid,2026-01-01T01:00:00Z", "invalid"),
    ("test,received_at,reported_at\n", "no data"),
    ("test,received_at,reported_at\nA,2026-01-01T00:00:00Z", "column count"),
    ("test,test,received_at,reported_at\n", "duplicate"),
])
def test_invalid_input(text, part):
    with pytest.raises(ValueError, match=part):
        analyze_csv(text)


@pytest.mark.parametrize("threshold", [0, -1, float("nan"), float("inf")])
def test_bad_threshold(threshold):
    with pytest.raises(ValueError, match="positive"):
        analyze_csv(CSV, threshold)


def test_export_neutralizes_formula():
    text = 'test,received_at,reported_at,note\nCBC,2026-01-01T00:00:00Z,2026-01-01T00:20:00Z,"=HYPERLINK(""https://bad.example"")"\n'
    output = annotated_csv(analyze_csv(text))
    assert "'=HYPERLINK" in output
    assert "tat_minutes,breached,outlier" in output
