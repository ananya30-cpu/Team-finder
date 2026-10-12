"""
Stats and graph endpoints:
  GET /api/stats
"""

from flask import Blueprint, jsonify
from db import fetch_all, fetch_one
from auth import login_required

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/stats")
@login_required
def get_stats():
    """Dashboard totals + breakdowns for charts."""
    totals = fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM students) AS total_students,
            (SELECT COUNT(*) FROM projects) AS total_projects,
            (SELECT COUNT(*) FROM skills) AS total_skills,
            (SELECT COUNT(*) FROM teams) AS total_teams,
            (SELECT COUNT(*) FROM join_requests WHERE request_status = 'PENDING') AS pending_requests
        """
    )

    projects_per_domain = fetch_all(
        """
        SELECT domain, COUNT(*) AS project_count
        FROM projects
        GROUP BY domain
        ORDER BY project_count DESC
        """
    )

    students_per_experience = fetch_all(
        """
        SELECT experience_level, COUNT(*) AS student_count
        FROM students
        GROUP BY experience_level
        ORDER BY student_count DESC
        """
    )

    top_skills = fetch_all(
        """
        SELECT
            sk.skill_id,
            sk.skill_name,
            sk.skill_category,
            COUNT(ss.student_id) AS student_count
        FROM skills sk
        JOIN student_skills ss ON sk.skill_id = ss.skill_id
        GROUP BY sk.skill_id, sk.skill_name, sk.skill_category
        ORDER BY student_count DESC
        LIMIT 10
        """
    )

    return jsonify({
        "totals": totals,
        "projects_per_domain": projects_per_domain,
        "students_per_experience": students_per_experience,
        "top_skills": top_skills,
    })
