import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv("SECRET_KEY", "municipal-grievance-dev-key-2026")
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "grievances.db"))
    
    # SLA deadlines in hours by category and priority
    SLA_HOURS = {
        "High": 24,      # e.g., Open manhole, live wire, sewer overflow
        "Medium": 48,    # e.g., Pothole, streetlight cluster, garbage pile
        "Low": 72        # e.g., Pruning request, signage replacement
    }
    
    VALID_CATEGORIES = [
        "Roads & Potholes",
        "Solid Waste Management",
        "Drainage & Sewage",
        "Street Lighting",
        "Water Supply",
        "Public Health & Sanitation"
    ]
    
    VALID_STATUSES = [
        "SUBMITTED",
        "ASSIGNED",
        "IN_PROGRESS",
        "RESOLVED",
        "REOPENED",
        "CLOSED"
    ]
    
    VALID_PRIORITIES = ["High", "Medium", "Low"]
