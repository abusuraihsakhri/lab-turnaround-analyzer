"""
Automated Pytest Test Suite for Lab Turnaround Analyzer.
Domain: AI Drug Discovery, Structural Biology & Wet-Lab Robotics
Standard: wwPDB / IUPAC / OpenSMILES / ISAC Standards
"""
import os
import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, AuditTrail, SecurityException
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_phi_guard_redaction():
    """Test PHI redaction replaces sensitive data."""
    text = "Patient John Doe MRN-123456 has appointment"
    redacted = PHIGuard.redact_phi(text)
    assert "REDACTED_IDENTIFIER" in redacted
    assert "MRN" not in redacted or "REDACTED" in redacted


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_audit_trail_random_key_generation():
    """Test that AuditTrail generates a random key when no secret is provided."""
    # Clear any existing env var
    old_key = os.environ.pop("AUDIT_SECRET_KEY", None)
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            trail = AuditTrail()
            # Should have issued a warning about missing AUDIT_SECRET_KEY
            assert any("AUDIT_SECRET_KEY" in str(warning.message) for warning in w)
        # Verify trail still functions with random key
        entry = trail.log("test", "test_tier", "TEST_EVENT", {"data": "value"})
        assert entry["current_hash"] != ""
        assert trail.verify_integrity() is True
    finally:
        if old_key:
            os.environ["AUDIT_SECRET_KEY"] = old_key


def test_audit_trail_with_explicit_key():
    """Test that AuditTrail uses provided key correctly."""
    trail = AuditTrail(secret_key="test-secret-key-for-unit-test")
    entry = trail.log("test", "test_tier", "TEST_EVENT", {"data": "value"})
    assert entry["current_hash"] != ""
    assert trail.verify_integrity() is True
