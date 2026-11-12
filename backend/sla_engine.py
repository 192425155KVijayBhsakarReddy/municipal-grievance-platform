from datetime import datetime, timedelta, timezone
from backend.config import Config

def calculate_sla_deadline(priority: str, start_time: datetime | None = None) -> datetime:
    """Calculates SLA deadline based on priority (High=24h, Medium=48h, Low=72h)."""
    base = start_time or datetime.now(timezone.utc)
    hours = Config.SLA_HOURS.get(priority, Config.SLA_HOURS["Medium"])
    return base + timedelta(hours=hours)

def evaluate_sla_status(deadline_iso: str, current_status: str) -> dict:
    """Evaluates whether an active grievance is within SLA, near breach, or breached."""
    if current_status in ["RESOLVED", "CLOSED"]:
        return {"is_breached": False, "status_label": "Fulfilled", "hours_remaining": 0}
        
    try:
        deadline = datetime.fromisoformat(deadline_iso)
        now = datetime.now(timezone.utc)
        diff = deadline - now
        hours_remaining = diff.total_seconds() / 3600.0
        
        if hours_remaining < 0:
            return {
                "is_breached": True,
                "status_label": "BREACHED",
                "hours_remaining": round(hours_remaining, 1)
            }
        elif hours_remaining <= 6:
            return {
                "is_breached": False,
                "status_label": "NEAR_BREACH",
                "hours_remaining": round(hours_remaining, 1)
            }
        else:
            return {
                "is_breached": False,
                "status_label": "ON_TRACK",
                "hours_remaining": round(hours_remaining, 1)
            }
    except Exception:
        return {"is_breached": False, "status_label": "UNKNOWN", "hours_remaining": 0}
