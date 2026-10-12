"""
Join-request endpoints (all require login).
Sender / list student id always comes from the JWT (g.student_id).
"""

from flask import Blueprint, jsonify, request, g
import mysql.connector

from db import fetch_all, fetch_one, execute_write, call_procedure
from auth import login_required

join_requests_bp = Blueprint("join_requests", __name__)


@join_requests_bp.post("/join-requests")
@login_required
def create_join_request():
    """
    Body: {project_id, message}
    sender = logged-in student; receiver = project creator.
    """
    data = request.get_json(silent=True) or {}
    project_id = data.get("project_id")
    sender_id = g.student_id
    message = data.get("message") or ""

    if not project_id:
        return jsonify({"error": "project_id is required"}), 400

    project = fetch_one(
        """
        SELECT project_id, created_by, project_status, project_title
        FROM projects
        WHERE project_id = %s
        """,
        (project_id,),
    )
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if int(sender_id) == int(project["created_by"]):
        return jsonify({"error": "You cannot request to join your own project"}), 400

    if project["project_status"] == "FULL":
        return jsonify({"error": "This project team is already full"}), 400

    existing = fetch_one(
        """
        SELECT request_id FROM join_requests
        WHERE project_id = %s AND sender_student_id = %s
        """,
        (project_id, sender_id),
    )
    if existing:
        return jsonify({"error": "You already sent a join request for this project"}), 400

    sql = """
        INSERT INTO join_requests
            (project_id, sender_student_id, receiver_student_id, message, request_status)
        VALUES (%s, %s, %s, %s, 'PENDING')
    """
    params = (project_id, sender_id, project["created_by"], message)

    try:
        _, request_id = execute_write(sql, params)
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({"error": "You already sent a join request for this project"}), 400
        return jsonify({"error": err.msg}), 400

    return jsonify({
        "request_id": request_id,
        "project_id": project_id,
        "sender_id": sender_id,
        "receiver_id": project["created_by"],
        "message": message,
        "request_status": "PENDING",
    }), 201


@join_requests_bp.get("/join-requests")
@login_required
def list_join_requests():
    """
    ?type=received|sent (default received)
    Uses the logged-in student from the JWT.
    """
    student_id = g.student_id
    req_type = (request.args.get("type") or "received").lower()

    if req_type == "sent":
        where = "jr.sender_student_id = %s"
    else:
        where = "jr.receiver_student_id = %s"

    rows = fetch_all(
        f"""
        SELECT
            jr.request_id,
            jr.project_id,
            p.project_title,
            jr.sender_student_id,
            CONCAT(s1.first_name, ' ', s1.last_name) AS sender_name,
            jr.receiver_student_id,
            CONCAT(s2.first_name, ' ', s2.last_name) AS receiver_name,
            jr.message,
            jr.request_status,
            jr.requested_at,
            jr.responded_at
        FROM join_requests jr
        JOIN projects p ON jr.project_id = p.project_id
        JOIN students s1 ON jr.sender_student_id = s1.student_id
        JOIN students s2 ON jr.receiver_student_id = s2.student_id
        WHERE {where}
        ORDER BY jr.requested_at DESC
        """,
        (student_id,),
    )
    return jsonify(rows)


@join_requests_bp.post("/join-requests/<int:request_id>/accept")
@login_required
def accept_join_request(request_id):
    """CALL accept_join_request — only the receiver (logged-in) should accept."""
    jr = fetch_one(
        """
        SELECT request_id, project_id, receiver_student_id
        FROM join_requests WHERE request_id = %s
        """,
        (request_id,),
    )
    if not jr:
        return jsonify({"error": "Join request not found"}), 404

    if int(jr["receiver_student_id"]) != int(g.student_id):
        return jsonify({"error": "Only the project owner can accept this request"}), 403

    try:
        call_procedure("accept_join_request", [request_id])
    except mysql.connector.Error as err:
        return jsonify({"error": err.msg}), 400

    updated = fetch_one(
        """
        SELECT request_id, request_status, responded_at, project_id
        FROM join_requests WHERE request_id = %s
        """,
        (request_id,),
    )

    return jsonify(updated)


@join_requests_bp.post("/join-requests/<int:request_id>/reject")
@login_required
def reject_join_request(request_id):
    """CALL reject_join_request — only the receiver can reject."""
    jr = fetch_one(
        """
        SELECT request_id, project_id, receiver_student_id
        FROM join_requests WHERE request_id = %s
        """,
        (request_id,),
    )
    if not jr:
        return jsonify({"error": "Join request not found"}), 404

    if int(jr["receiver_student_id"]) != int(g.student_id):
        return jsonify({"error": "Only the project owner can reject this request"}), 403

    try:
        call_procedure("reject_join_request", [request_id])
    except mysql.connector.Error as err:
        return jsonify({"error": err.msg}), 400

    updated = fetch_one(
        """
        SELECT request_id, request_status, responded_at, project_id
        FROM join_requests WHERE request_id = %s
        """,
        (request_id,),
    )

    return jsonify(updated)
