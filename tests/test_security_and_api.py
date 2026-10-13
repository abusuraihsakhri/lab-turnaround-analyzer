"""Security, CLI, and REST regression checks."""
import csv
from fastapi.testclient import TestClient

from agents.api import app
from agents.base import AuditTrail
from cli import main

INPUT = ("test,received_at,reported_at\n"
         "CBC,2026-01-01T08:00:00Z,2026-01-01T09:05:00Z\n")


def test_integrity_checks_hmac_not_only_links():
    trail = AuditTrail(secret_key="unit-test-key")
    trail.log("audit", "worker", "EVENT", {"status": "OK"})
    assert trail.verify_integrity()
    trail.logs[0]["actor"] = "tampered"
    assert not trail.verify_integrity()


def test_trail_getter_returns_defensive_copies():
    trail = AuditTrail(secret_key="unit-test-key")
    trail.log("audit", "worker", "EVENT", {"status": "OK"})
    trail.get_trail()[0]["actor"] = "mutated externally"
    assert trail.verify_integrity()


def test_tat_api_aggregates_without_leaking_raw_rows():
    client = TestClient(app)
    response = client.post("/api/tat/analyze", json={"csv_text": INPUT, "threshold_minutes": 60})
    assert response.status_code == 200
    data = response.json()
    assert data["overall"]["breach_count"] == 1
    assert data["overall"]["p50_minutes"] == 65
    assert "records" not in data
    assert "csv_text" not in data
    bad = client.post("/api/tat/analyze", json={"csv_text": INPUT, "threshold_minutes": -1})
    assert bad.status_code == 422


def test_tat_cli_output(tmp_path):
    inp, out, report = (tmp_path / "input.csv", tmp_path / "annotated.csv", tmp_path / "summary.json")
    inp.write_text(INPUT, encoding="utf-8")
    assert main(["analyze-tat", "--input", str(inp), "--output", str(out),
                 "--report", str(report)]) == 0
    with out.open(newline="", encoding="utf-8") as f:
        result = list(csv.DictReader(f))
    assert result[0]["tat_minutes"] == "65.0"
    assert '"breach_count": 1' in report.read_text(encoding="utf-8")


def test_csv_batch_false_string_is_not_truthy(tmp_path):
    inp, out = tmp_path / "agent.csv", tmp_path / "output.csv"
    inp.write_text("task_id,target_identifier,primary_metric,secondary_metric,status_descriptor,is_critical_flag\n"
                   "TASK-FLAG,TEST-01,10,1,NOMINAL,False\n", encoding="utf-8")
    assert main(["batch", "--input", str(inp), "--output", str(out)]) == 0
    with out.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["overall_urgency"] == "ROUTINE"
