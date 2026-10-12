"""
Auth routes (public: login + register; protected: /auth/me)

Passwords are hashed with werkzeug.security — never stored in plain text.
"""

import re
import time
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request, g
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

from auth import create_token, login_required, student_public_dict
from db import fetch_one, get_connection

auth_bp = Blueprint("auth", __name__)

# Simple email check (good enough for a college demo / viva)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ---------------------------------------------------------------------------
# In-memory rate limit: 5 failed logins per email per 60 seconds
# (resets when the Flask process restarts — fine for a student project)
# ---------------------------------------------------------------------------
_failed_logins = defaultdict(list)  # email -> [timestamps]


def _prune_failures(email, now, window=60):
    _failed_logins[email] = [t for t in _failed_logins[email] if now - t < window]


def _too_many_failures(email):
    now = time.time()
    _prune_failures(email, now)
    return len(_failed_logins[email]) >= 5


def _record_failure(email):
    _failed_logins[email].append(time.time())


def _clear_failures(email):
    _failed_logins.pop(email, None)


def _fetch_student_by_id(student_id):
    return fetch_one(
        """
        SELECT
            s.student_id, s.first_name, s.last_name, s.email, s.department_id,
            d.department_name, d.department_code,
            s.year_of_study, s.college, s.bio, s.github_portfolio,
            s.experience_level, s.availability_status, s.account_status, s.created_at
        FROM students s
        LEFT JOIN departments d ON s.department_id = d.department_id
        WHERE s.student_id = %s
        """,
        (student_id,),
    )


@auth_bp.post("/auth/login")
def login():
    """
    Body: {email, password}
    Returns: {token, student}
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    if _too_many_failures(email):
        return jsonify({
            "error": "Too many failed login attempts. Try again in a minute.",
        }), 429

    # Look up by email only (password checked in Python against the hash)
    sql = """
        SELECT
            s.student_id, s.first_name, s.last_name, s.email, s.password_hash,
            s.department_id, d.department_name, d.department_code,
            s.year_of_study, s.college, s.bio, s.github_portfolio,
            s.experience_level, s.availability_status, s.account_status, s.created_at
        FROM students s
        LEFT JOIN departments d ON s.department_id = d.department_id
        WHERE s.email = %s
    """
    row = fetch_one(sql, (email,))

    # Same generic message whether email is missing OR password is wrong
    # (avoids leaking which accounts exist)
    if not row or not check_password_hash(row["password_hash"], password):
        _record_failure(email)
        return jsonify({"error": "Invalid email or password"}), 401

    # Account status checks — clear messages for blocked/suspended
    status = (row.get("account_status") or "ACTIVE").upper()
    if status == "BLOCKED":
        return jsonify({"error": "Your account is blocked. Contact an administrator."}), 403
    if status == "SUSPENDED":
        return jsonify({"error": "Your account is suspended. Contact an administrator."}), 403

    _clear_failures(email)
    token = create_token(row["student_id"])
    student = student_public_dict(row)

    return jsonify({
        "token": token,
        "student": student,
    })


@auth_bp.post("/auth/register")
def register():
    """
    Body: {first_name, last_name, email, password, department_id, year_of_study}
    Creates a student with a hashed password and returns a JWT.
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Registration fields must be sent as an object"}), 400
    first_name = data.get("first_name") or ""
    last_name = data.get("last_name") or ""
    email = data.get("email") or ""
    password = data.get("password") or ""
    if not all(isinstance(value, str) for value in (first_name, last_name, email, password)):
        return jsonify({"error": "Name, email, and password values must be text"}), 400
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip().lower()
    department_id = data.get("department_id")
    year_of_study = data.get("year_of_study")

    if not all([first_name, last_name, email, password, department_id, year_of_study]):
        return jsonify({
            "error": "first_name, last_name, email, password, department_id, and year_of_study are required",
        }), 400

    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    if len(first_name) > 50 or len(last_name) > 50 or len(email) > 150:
        return jsonify({"error": "Name or email is too long"}), 400
    try:
        # Reject fractional numeric values instead of silently truncating them.
        if isinstance(department_id, bool) or isinstance(year_of_study, bool):
            raise ValueError()
        department_number = Decimal(str(department_id))
        year_number = Decimal(str(year_of_study))
        if not department_number.is_finite() or department_number != department_number.to_integral_value():
            raise ValueError()
        if not year_number.is_finite() or year_number != year_number.to_integral_value():
            raise ValueError()
        department_id = int(department_number)
        year_of_study = int(year_number)
    except (TypeError, ValueError, InvalidOperation):
        return jsonify({"error": "Choose a valid department and year"}), 400
    if not 1 <= year_of_study <= 4:
        return jsonify({"error": "Year of study must be between 1 and 4"}), 400

    optional_text = {}
    for field in ("bio", "github_portfolio", "college"):
        value = data.get(field) or ""
        if not isinstance(value, str):
            return jsonify({"error": f"{field} must be text"}), 400
        optional_text[field] = value.strip() or None
    bio = optional_text["bio"]
    github_portfolio = optional_text["github_portfolio"]
    college = optional_text["college"]
    experience_level = str(data.get("experience_level") or "BEGINNER").upper()
    if bio and len(bio) > 500:
        return jsonify({"error": "Bio must be 500 characters or fewer"}), 400
    if github_portfolio and len(github_portfolio) > 255:
        return jsonify({"error": "GitHub link must be 255 characters or fewer"}), 400
    if college and len(college) > 150:
        return jsonify({"error": "College must be 150 characters or fewer"}), 400
    if experience_level not in {"BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"}:
        return jsonify({"error": "Choose a valid experience level"}), 400

    submitted_skills = data.get("skills") or []
    if not isinstance(submitted_skills, list):
        return jsonify({"error": "Skills must be a list"}), 400
    normalized_skills = []
    seen_skill_ids = set()
    for item in submitted_skills:
        try:
            raw_skill_id = item.get("skill_id")
            skill_number = Decimal(str(raw_skill_id))
            if isinstance(raw_skill_id, bool) or not skill_number.is_finite() or skill_number != skill_number.to_integral_value():
                raise ValueError()
            skill_id = int(skill_number)
            years = Decimal(str(item.get("years_of_experience", 0)))
        except (AttributeError, TypeError, ValueError, InvalidOperation):
            return jsonify({"error": "Each skill needs a valid id and years of experience"}), 400
        proficiency = str(item.get("proficiency_level") or "BEGINNER").upper()
        if skill_id in seen_skill_ids:
            return jsonify({"error": "A skill can only be selected once"}), 400
        if proficiency not in {"BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"}:
            return jsonify({"error": "Choose a valid proficiency for every skill"}), 400
        if not years.is_finite() or years < 0 or years > 20:
            return jsonify({"error": "Years of experience must be between 0 and 20"}), 400
        seen_skill_ids.add(skill_id)
        normalized_skills.append((skill_id, proficiency, years))

    # Hash before insert — plain password never touches the database
    password_hash = generate_password_hash(password)

    sql = """
        INSERT INTO students
            (first_name, last_name, email, password_hash, department_id, year_of_study,
             bio, github_portfolio, college, experience_level, account_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        first_name, last_name, email, password_hash, department_id, year_of_study,
        bio, github_portfolio, college, experience_level, "ACTIVE",
    )
    connection = get_connection()
    cursor = connection.cursor()
    try:
        department_sql = "SELECT department_id FROM departments WHERE department_id = %s"
        cursor.execute(department_sql, (department_id,))
        if not cursor.fetchone():
            connection.rollback()
            return jsonify({"error": "Department not found"}), 400
        if normalized_skills:
            placeholders = ", ".join(["%s"] * len(normalized_skills))
            skills_sql = f"SELECT skill_id FROM skills WHERE skill_id IN ({placeholders})"
            cursor.execute(skills_sql, tuple(item[0] for item in normalized_skills))
            found_skill_ids = {row[0] for row in cursor.fetchall()}
            if found_skill_ids != seen_skill_ids:
                connection.rollback()
                return jsonify({"error": "One or more selected skills do not exist"}), 400
        cursor.execute(sql, params)
        new_id = cursor.lastrowid

        skill_sql = """
            INSERT INTO student_skills
                (student_id, skill_id, proficiency_level, years_of_experience)
            VALUES (%s, %s, %s, %s)
        """
        for skill_id, proficiency, years in normalized_skills:
            skill_params = (new_id, skill_id, proficiency, years)
            cursor.execute(skill_sql, skill_params)

        connection.commit()
    except mysql.connector.Error as err:
        connection.rollback()
        if err.errno == 1062:
            return jsonify({"error": "An account with this email already exists"}), 400
        return jsonify({"error": err.msg}), 400
    finally:
        cursor.close()
        connection.close()

    student = _fetch_student_by_id(new_id)
    token = create_token(new_id)

    return jsonify({
        "token": token,
        "student": student_public_dict(student),
    }), 201


@auth_bp.get("/auth/me")
@login_required
def me():
    """Return the logged-in student (id comes from the JWT)."""
    student = _fetch_student_by_id(g.student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(student_public_dict(student))
