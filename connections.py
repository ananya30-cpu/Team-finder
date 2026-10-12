"""
Network graph data:
  GET /api/connections  → {nodes, edges}
"""

from flask import Blueprint, jsonify
from db import fetch_all
from auth import login_required

connections_bp = Blueprint("connections", __name__)


@connections_bp.get("/connections")
@login_required
def get_connections():
    """
    Nodes = students; edges = team_connections rows.
    Useful for a force-directed graph on the frontend.
    """
    nodes = fetch_all(
        """
        SELECT
            s.student_id AS id,
            CONCAT(s.first_name, ' ', s.last_name) AS label,
            s.experience_level,
            s.availability_status,
            d.department_code
        FROM students s
        JOIN departments d ON s.department_id = d.department_id
        WHERE s.account_status = 'ACTIVE'
        """
    )

    edges = fetch_all(
        """
        SELECT
            connection_id,
            student_id_1 AS source,
            student_id_2 AS target,
            connection_strength AS weight,
            connection_type
        FROM team_connections
        """
    )

    return jsonify({"nodes": nodes, "edges": edges})
