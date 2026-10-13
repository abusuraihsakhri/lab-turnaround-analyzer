"""
FastAPI REST API Server for Lab Turnaround Analyzer.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor
from tat_metrics import analyze_csv

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Lab Turnaround Analyzer API",
    description="Laboratory turnaround metrics and preserved legacy agent evaluation API",
    version="3.1.0",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "lab-turnaround-analyzer", "domain": "Laboratory informatics", "standard": "Descriptive laboratory operations metrics", "version": "3.1.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


class TatRequest(BaseModel):
    csv_text: str
    threshold_minutes: float = 60.0


@app.post("/api/tat/analyze")
def api_tat_analyze(request: TatRequest):
    """Aggregate turnaround metrics without returning specimen-level source rows."""
    try:
        result = analyze_csv(request.csv_text, request.threshold_minutes)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {key: result[key] for key in ("threshold_minutes", "overall", "by_test")}


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
