from datetime import datetime, timedelta, timezone
from backend.sla_engine import calculate_sla_deadline, evaluate_sla_status

def test_sla_deadline_calculation():
    now = datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc)
    
    high_deadline = calculate_sla_deadline("High", now)
    assert high_deadline == now + timedelta(hours=24)
    
    med_deadline = calculate_sla_deadline("Medium", now)
    assert med_deadline == now + timedelta(hours=48)
    
    low_deadline = calculate_sla_deadline("Low", now)
    assert low_deadline == now + timedelta(hours=72)

def test_sla_evaluation_on_track():
    future_deadline = (datetime.now(timezone.utc) + timedelta(hours=30)).isoformat()
    status = evaluate_sla_status(future_deadline, "IN_PROGRESS")
    assert status["is_breached"] is False
    assert status["status_label"] == "ON_TRACK"
    assert status["hours_remaining"] > 25

def test_sla_evaluation_breached():
    past_deadline = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    status = evaluate_sla_status(past_deadline, "SUBMITTED")
    assert status["is_breached"] is True
    assert status["status_label"] == "BREACHED"
    assert status["hours_remaining"] < 0

def test_sla_evaluation_fulfilled_when_resolved():
    past_deadline = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    status = evaluate_sla_status(past_deadline, "RESOLVED")
    assert status["is_breached"] is False
    assert status["status_label"] == "Fulfilled"
