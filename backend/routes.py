from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from backend.config import Config
from backend.database import db_session
from backend.models import generate_tracking_id, validate_complaint_payload
from backend.sla_engine import calculate_sla_deadline, evaluate_sla_status

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

@api_bp.route("/healthz", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "municipal-grievance-platform",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

@api_bp.route("/complaints", methods=["POST"])
def create_complaint():
    data = request.get_json(silent=True) or {}
    is_valid, error_msg = validate_complaint_payload(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 400
        
    category = data["category"]
    if category not in Config.VALID_CATEGORIES:
        return jsonify({"error": f"Invalid category. Allowed: {Config.VALID_CATEGORIES}"}), 400
        
    priority = data.get("priority", "Medium")
    if priority not in Config.VALID_PRIORITIES:
        priority = "Medium"
        
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    sla_deadline = calculate_sla_deadline(priority, now).isoformat()
    tracking_id = generate_tracking_id()
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaints (
                tracking_id, citizen_name, citizen_phone, category, ward, location,
                description, photo_url, priority, status, created_at, updated_at, sla_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUBMITTED', ?, ?, ?)
        """, (
            tracking_id,
            data["citizen_name"].strip(),
            data["citizen_phone"].strip(),
            category,
            data["ward"].strip(),
            data["location"].strip(),
            data["description"].strip(),
            data.get("photo_url", "").strip(),
            priority,
            now_iso,
            now_iso,
            sla_deadline
        ))
        
        cursor.execute("""
            INSERT INTO audit_logs (tracking_id, action, from_status, to_status, performed_by, timestamp, notes)
            VALUES (?, 'CREATED', NULL, 'SUBMITTED', 'Citizen', ?, 'Grievance submitted successfully')
        """, (tracking_id, now_iso))
        
    return jsonify({
        "message": "Grievance submitted successfully",
        "tracking_id": tracking_id,
        "status": "SUBMITTED",
        "priority": priority,
        "sla_deadline": sla_deadline,
        "created_at": now_iso
    }), 201

@api_bp.route("/complaints/<tracking_id>", methods=["GET"])
def get_complaint(tracking_id):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE tracking_id = ?", (tracking_id.strip(),))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Complaint not found"}), 404
            
        complaint = dict(row)
        sla_info = evaluate_sla_status(complaint["sla_deadline"], complaint["status"])
        complaint["sla_analysis"] = sla_info
        
        # Get audit logs
        cursor.execute("SELECT action, from_status, to_status, performed_by, timestamp, notes FROM audit_logs WHERE tracking_id = ? ORDER BY id ASC", (tracking_id,))
        complaint["timeline"] = [dict(r) for r in cursor.fetchall()]
        
        # Get feedback if any
        cursor.execute("SELECT rating, comments, submitted_at FROM feedback WHERE tracking_id = ?", (tracking_id,))
        fb = cursor.fetchone()
        complaint["feedback"] = dict(fb) if fb else None
        
    return jsonify(complaint), 200

@api_bp.route("/complaints", methods=["GET"])
def list_complaints():
    status_filter = request.args.get("status")
    ward_filter = request.args.get("ward")
    category_filter = request.args.get("category")
    
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if ward_filter:
        query += " AND ward = ?"
        params.append(ward_filter)
    if category_filter:
        query += " AND category = ?"
        params.append(category_filter)
        
    query += " ORDER BY id DESC"
    
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            item = dict(r)
            item["sla_analysis"] = evaluate_sla_status(item["sla_deadline"], item["status"])
            results.append(item)
            
    return jsonify({"count": len(results), "complaints": results}), 200

@api_bp.route("/complaints/<tracking_id>/assign", methods=["PATCH"])
def assign_complaint(tracking_id):
    data = request.get_json(silent=True) or {}
    engineer = str(data.get("assigned_engineer", "")).strip()
    if not engineer:
        return jsonify({"error": "Field 'assigned_engineer' is required"}), 400
        
    now_iso = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM complaints WHERE tracking_id = ?", (tracking_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Complaint not found"}), 404
            
        old_status = row["status"]
        new_status = "ASSIGNED"
        
        cursor.execute("""
            UPDATE complaints
            SET assigned_engineer = ?, status = ?, updated_at = ?
            WHERE tracking_id = ?
        """, (engineer, new_status, now_iso, tracking_id))
        
        cursor.execute("""
            INSERT INTO audit_logs (tracking_id, action, from_status, to_status, performed_by, timestamp, notes)
            VALUES (?, 'ASSIGNED', ?, ?, 'Helpdesk Staff', ?, ?)
        """, (tracking_id, old_status, new_status, now_iso, f"Assigned to {engineer}"))
        
    return jsonify({
        "message": f"Assigned to {engineer}",
        "tracking_id": tracking_id,
        "status": new_status,
        "assigned_engineer": engineer
    }), 200

@api_bp.route("/complaints/<tracking_id>/status", methods=["PATCH"])
def update_complaint_status(tracking_id):
    data = request.get_json(silent=True) or {}
    new_status = str(data.get("status", "")).strip().upper()
    notes = str(data.get("notes", "")).strip()
    proof = str(data.get("resolution_proof", "")).strip()
    actor = str(data.get("performed_by", "Field Engineer")).strip()
    
    if new_status not in Config.VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Allowed: {Config.VALID_STATUSES}"}), 400
        
    now_iso = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM complaints WHERE tracking_id = ?", (tracking_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Complaint not found"}), 404
            
        old_status = row["status"]
        
        cursor.execute("""
            UPDATE complaints
            SET status = ?, resolution_notes = COALESCE(NULLIF(?, ''), resolution_notes),
                resolution_proof = COALESCE(NULLIF(?, ''), resolution_proof),
                updated_at = ?
            WHERE tracking_id = ?
        """, (new_status, notes, proof, now_iso, tracking_id))
        
        cursor.execute("""
            INSERT INTO audit_logs (tracking_id, action, from_status, to_status, performed_by, timestamp, notes)
            VALUES (?, 'STATUS_UPDATE', ?, ?, ?, ?, ?)
        """, (tracking_id, old_status, new_status, actor, now_iso, notes or f"Status changed to {new_status}"))
        
    return jsonify({
        "message": "Status updated successfully",
        "tracking_id": tracking_id,
        "previous_status": old_status,
        "new_status": new_status
    }), 200

@api_bp.route("/complaints/<tracking_id>/feedback", methods=["POST"])
def submit_feedback(tracking_id):
    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    comments = str(data.get("comments", "")).strip()
    reopen = bool(data.get("reopen", False))
    
    try:
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Rating is required and must be an integer (1-5)"}), 400
        
    now_iso = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM complaints WHERE tracking_id = ?", (tracking_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Complaint not found"}), 404
            
        cursor.execute("""
            INSERT OR REPLACE INTO feedback (tracking_id, rating, comments, submitted_at)
            VALUES (?, ?, ?, ?)
        """, (tracking_id, rating_int, comments, now_iso))
        
        if reopen:
            cursor.execute("UPDATE complaints SET status = 'REOPENED', updated_at = ? WHERE tracking_id = ?", (now_iso, tracking_id))
            cursor.execute("""
                INSERT INTO audit_logs (tracking_id, action, from_status, to_status, performed_by, timestamp, notes)
                VALUES (?, 'REOPENED', 'RESOLVED', 'REOPENED', 'Citizen', ?, ?)
            """, (tracking_id, now_iso, f"Citizen dissatisfied (Rating {rating_int}/5): {comments}"))
        elif row["status"] == "RESOLVED":
            cursor.execute("UPDATE complaints SET status = 'CLOSED', updated_at = ? WHERE tracking_id = ?", (now_iso, tracking_id))
            cursor.execute("""
                INSERT INTO audit_logs (tracking_id, action, from_status, to_status, performed_by, timestamp, notes)
                VALUES (?, 'CLOSED', 'RESOLVED', 'CLOSED', 'Citizen', ?, ?)
            """, (tracking_id, now_iso, f"Citizen confirmed resolution (Rating {rating_int}/5)"))
            
    return jsonify({
        "message": "Feedback submitted successfully",
        "tracking_id": tracking_id,
        "rating": rating_int,
        "status": "REOPENED" if reopen else "CLOSED"
    }), 200

@api_bp.route("/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    with db_session() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) AS total FROM complaints")
        total = cursor.fetchone()["total"]
        
        cursor.execute("SELECT status, COUNT(*) AS count FROM complaints GROUP BY status")
        by_status = {r["status"]: r["count"] for r in cursor.fetchall()}
        
        cursor.execute("SELECT ward, COUNT(*) AS count FROM complaints GROUP BY ward")
        by_ward = {r["ward"]: r["count"] for r in cursor.fetchall()}
        
        cursor.execute("SELECT category, COUNT(*) AS count FROM complaints GROUP BY category")
        by_category = {r["category"]: r["count"] for r in cursor.fetchall()}
        
        cursor.execute("SELECT AVG(rating) AS avg_rating, COUNT(*) AS count FROM feedback")
        fb_row = cursor.fetchone()
        avg_rating = round(fb_row["avg_rating"] or 0, 2)
        total_feedback = fb_row["count"]
        
    return jsonify({
        "total_complaints": total,
        "by_status": by_status,
        "by_ward": by_ward,
        "by_category": by_category,
        "average_citizen_rating": avg_rating,
        "total_feedback_count": total_feedback
    }), 200
