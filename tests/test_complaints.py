import os
import tempfile
import pytest
from backend.app import create_app
from backend.database import init_db

@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    
    with app.test_client() as client:
        yield client
        
    os.close(db_fd)
    if os.path.exists(db_path):
        os.remove(db_path)

def test_healthz(client):
    res = client.get("/api/v1/healthz")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "municipal-grievance-platform"

def test_create_complaint_success(client):
    payload = {
        "citizen_name": "K. Vijay Bhaskar Reddy",
        "citizen_phone": "9876543210",
        "category": "Roads & Potholes",
        "ward": "Ward 101 - Central",
        "location": "Main Trunk Road, Near SIMATS Gate",
        "description": "Deep pothole causing traffic obstruction and waterlogging.",
        "priority": "High"
    }
    res = client.post("/api/v1/complaints", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert "tracking_id" in data
    assert data["status"] == "SUBMITTED"
    assert data["priority"] == "High"
    assert data["tracking_id"].startswith("GRV-")

def test_create_complaint_boundary_description_too_short(client):
    payload = {
        "citizen_name": "K. Vijay",
        "citizen_phone": "9876543210",
        "category": "Roads & Potholes",
        "ward": "Ward 101 - Central",
        "location": "Main Road",
        "description": "Short"  # Less than 10 characters
    }
    res = client.post("/api/v1/complaints", json=payload)
    assert res.status_code == 400
    assert "Description too short" in res.get_json()["error"]

def test_create_complaint_invalid_phone(client):
    payload = {
        "citizen_name": "K. Vijay",
        "citizen_phone": "123",  # Invalid phone
        "category": "Roads & Potholes",
        "ward": "Ward 101 - Central",
        "location": "Main Road",
        "description": "Valid description for reporting an issue."
    }
    res = client.post("/api/v1/complaints", json=payload)
    assert res.status_code == 400
    assert "Invalid phone number" in res.get_json()["error"]

def test_assign_and_lifecycle_flow(client):
    # 1. Create
    payload = {
        "citizen_name": "Citizen User",
        "citizen_phone": "9123456789",
        "category": "Street Lighting",
        "ward": "Ward 102 - North Zone",
        "location": "Cross Street 3",
        "description": "Streetlight pole flickering repeatedly at night.",
        "priority": "Medium"
    }
    create_res = client.post("/api/v1/complaints", json=payload)
    tracking_id = create_res.get_json()["tracking_id"]
    
    # 2. Assign engineer
    assign_res = client.patch(f"/api/v1/complaints/{tracking_id}/assign", json={
        "assigned_engineer": "Er. K. Suresh"
    })
    assert assign_res.status_code == 200
    assert assign_res.get_json()["status"] == "ASSIGNED"
    
    # 3. Engineer updates to IN_PROGRESS
    status_res = client.patch(f"/api/v1/complaints/{tracking_id}/status", json={
        "status": "IN_PROGRESS",
        "notes": "Bulb wiring replaced, testing current."
    })
    assert status_res.status_code == 200
    assert status_res.get_json()["new_status"] == "IN_PROGRESS"
    
    # 4. Engineer marks RESOLVED
    res_res = client.patch(f"/api/v1/complaints/{tracking_id}/status", json={
        "status": "RESOLVED",
        "notes": "Bulb replaced and functional.",
        "resolution_proof": "https://example.com/proof.jpg"
    })
    assert res_res.status_code == 200
    assert res_res.get_json()["new_status"] == "RESOLVED"
    
    # 5. Citizen gives 5-star feedback -> CLOSED
    fb_res = client.post(f"/api/v1/complaints/{tracking_id}/feedback", json={
        "rating": 5,
        "comments": "Fixed very fast. Excellent work!",
        "reopen": False
    })
    assert fb_res.status_code == 200
    assert fb_res.get_json()["status"] == "CLOSED"
    
    # Verify final timeline in GET
    get_res = client.get(f"/api/v1/complaints/{tracking_id}")
    complaint_data = get_res.get_json()
    assert complaint_data["status"] == "CLOSED"
    assert len(complaint_data["timeline"]) >= 4
