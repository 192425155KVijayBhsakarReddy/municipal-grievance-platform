import re
import random
from datetime import datetime, timezone

def generate_tracking_id() -> str:
    """Generates unique human-readable tracking ID: GRV-2026-XXXXX"""
    year = datetime.now().year
    suffix = random.randint(10000, 99999)
    return f"GRV-{year}-{suffix}"

def validate_complaint_payload(data: dict) -> tuple[bool, str | None]:
    """Validates complaint intake request data against business constraints."""
    if not isinstance(data, dict):
        return False, "Payload must be a valid JSON object."
    
    required_fields = ["citizen_name", "citizen_phone", "category", "ward", "location", "description"]
    for field in required_fields:
        val = str(data.get(field, "")).strip()
        if not val:
            return False, f"Field '{field}' is required and cannot be empty."
    
    # Phone number validation (10 digits)
    phone = str(data.get("citizen_phone", "")).strip()
    if not re.match(r"^\+?[0-9]{10,13}$", phone):
        return False, "Invalid phone number format. Must contain 10-13 digits."
    
    # Description boundary check (min 10 chars, max 1000 chars)
    desc = str(data.get("description", "")).strip()
    if len(desc) < 10:
        return False, "Description too short; must be at least 10 characters."
    if len(desc) > 1000:
        return False, "Description exceeds maximum allowed limit of 1000 characters."
        
    return True, None
