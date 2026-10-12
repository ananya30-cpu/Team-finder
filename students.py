"""
Student endpoints:
  GET /api/students
  GET /api/students/<id>
"""

from flask import Blueprint, jsonify, request
from db import fetch_all, fetch_one
from auth import login_required

students_bp = Blueprint("students", __name__)


@students_bp.get("/students")
@login_required
def list_students():
    """
    List students with optional filters:
      ?skill=Python (or skill id)
      ?department=COMP (name, code, or id)
      ?availability=AVAILABLE
      ?search=ananya (matches first/last name or email)
    """
    skill = request.args.get("skill")
    department = request.args.get("department")
    availability = request.args.get("availability")
    search = request.args.get("search")

    # Base query joins department so the UI can show the name
    sql = """
        SELECT DISTINCT
            s.student_id,
            s.first_name,
            s.last_name,
            s.email,
            s.department_id,
            d.department_name,
            d.department_code,
            s.year_of_study,
            s.college,
            s.bio,
            s.github_portfolio,
            s.experience_level,
            s.availability_status,
            s.account_status
        FROM students s
        JOIN departments d ON s.department_id = d.department_id
    """
    # Optional join when filtering by skill
    if skill:
        sql += """
            JOIN student_skills ss ON s.student_id = ss.student_id
            JOIN skills sk ON ss.skill_id = sk.skill_id
        """

    sql += " WHERE s.account_status = 'ACTIVE'"
    params = []

    if availability:
        sql += " AND s.availability_status = %s"
        params.append(availability)

    if department:
        # Accept id, code, or name
        sql += """ AND (
            d.department_id = %s
            OR d.department_code = %s
            OR d.department_name = %s
        )"""
        params.extend([department, department, department])

    if skill:
        sql += " AND (sk.skill_id = %s OR sk.skill_name = %s)"
        params.extend([skill, skill])

    if search:
        like = f"%{search}%"
        sql += """ AND (
            s.first_name LIKE %s
            OR s.last_name LIKE %s
            OR s.email LIKE %s
            OR CONCAT(s.first_name, ' ', s.last_name) LIKE %s
        )"""
        params.extend([like, like, like, like])

    sql += " ORDER BY s.first_name, s.last_name"

    rows = fetch_all(sql, tuple(params))
    return jsonify(rows)


@students_bp.get("/students/<int:student_id>")
@login_required
def get_student(student_id):
    """One student plus their skills list."""
    student = fetch_one(
        """
        SELECT
            s.student_id,
            s.first_name,
            s.last_name,
            s.email,
            s.department_id,
            d.department_name,
            d.department_code,
            s.year_of_study,
            s.college,
            s.bio,
            s.github_portfolio,
            s.experience_level,
            s.availability_status,
            s.account_status,
            s.created_at
        FROM students s
        JOIN departments d ON s.department_id = d.department_id
        WHERE s.student_id = %s
        """,
        (student_id,),
    )

    if not student:
        return jsonify({"error": "Student not found"}), 404

    skills = fetch_all(
        """
        SELECT
            sk.skill_id,
            sk.skill_name,
            sk.skill_category,
            ss.proficiency_level,
            ss.years_of_experience,
            ss.is_verified
        FROM student_skills ss
        JOIN skills sk ON ss.skill_id = sk.skill_id
        WHERE ss.student_id = %s
        ORDER BY sk.skill_name
        """,
        (student_id,),
    )
    student["skills"] = skills
    return jsonify(student)
