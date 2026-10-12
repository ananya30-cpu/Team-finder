"""
Authenticated "me" endpoints:
  GET /api/me/dashboard
"""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, g, request
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

from auth import login_required
from db import fetch_all, fetch_one, execute_write

me_bp = Blueprint("me", __name__)

# ENUM index order — same idea as (proficiency_level + 0) in SQL
PROF_RANK = {
    "BEGINNER": 1,
    "INTERMEDIATE": 2,
    "ADVANCED": 3,
    "EXPERT": 4,
}


def _rank(level):
    if not level:
        return 0
    return PROF_RANK.get(str(level).upper(), 0)


def _match_percent(required_rows, student_skill_map):
    """
    required_rows: list of {skill_id, importance_weight, minimum_proficiency}
    student_skill_map: {skill_id: proficiency_level string}
    """
    if not required_rows:
        return 0.0
    total = sum(r["importance_weight"] or 0 for r in required_rows)
    if total <= 0:
        return 0.0
    earned = 0
    for r in required_rows:
        sid = r["skill_id"]
        if sid not in student_skill_map:
            continue
        if _rank(student_skill_map[sid]) >= _rank(r["minimum_proficiency"]):
            earned += r["importance_weight"] or 0
    return round((earned / total) * 100, 1)


@me_bp.get("/me/dashboard")
@login_required
def my_dashboard():
    """
    Personal dashboard for the logged-in student (id from Bearer token).
    Uses parameterized SQL + project_match_view / project_details_view.
    """
    student_id = g.student_id

    # ------------------------------------------------------------------
    # Profile + skills (for strength + skill_gap)
    # ------------------------------------------------------------------
    sql_profile = """
        SELECT
            student_id, first_name, last_name, email, bio, github_portfolio,
            experience_level, availability_status, department_id
        FROM students
        WHERE student_id = %s
    """
    profile = fetch_one(sql_profile, (student_id,))
    if not profile:
        return jsonify({"error": "Student not found"}), 404

    sql_skills = """
        SELECT skill_id, proficiency_level, is_verified
        FROM student_skills
        WHERE student_id = %s
    """
    my_skills = fetch_all(sql_skills, (student_id,))
    skill_map = {s["skill_id"]: s["proficiency_level"] for s in my_skills}

    # Profile strength: 4 equal checks → percentage
    checks = []
    missing = []

    has_bio = bool(profile.get("bio") and str(profile["bio"]).strip())
    checks.append(has_bio)
    if not has_bio:
        missing.append("Add a bio")

    has_github = bool(profile.get("github_portfolio") and str(profile["github_portfolio"]).strip())
    checks.append(has_github)
    if not has_github:
        missing.append("Add a GitHub portfolio link")

    has_three_skills = len(my_skills) >= 3
    checks.append(has_three_skills)
    if not has_three_skills:
        missing.append("Add at least 3 skills")

    has_strong_skill = any(
        s.get("is_verified") or str(s.get("proficiency_level", "")).upper() == "ADVANCED"
        or str(s.get("proficiency_level", "")).upper() == "EXPERT"
        for s in my_skills
    )
    # Spec: ">=1 verified or ADVANCED skill" — count EXPERT as meeting ADVANCED bar too
    checks.append(has_strong_skill)
    if not has_strong_skill:
        missing.append("Verify a skill or reach ADVANCED proficiency on one skill")

    profile_strength = {
        "percentage": round(100.0 * sum(1 for c in checks if c) / len(checks), 1),
        "missing": missing,
        "checks": {
            "has_bio": has_bio,
            "has_github_portfolio": has_github,
            "has_at_least_3_skills": has_three_skills,
            "has_verified_or_advanced_skill": has_strong_skill,
        },
    }

    # ------------------------------------------------------------------
    # Pending received join requests
    # ------------------------------------------------------------------
    sql_pending = """
        SELECT
            jr.request_id,
            jr.project_id,
            p.project_title,
            jr.sender_student_id,
            CONCAT(s.first_name, ' ', s.last_name) AS sender_name,
            jr.message,
            jr.requested_at,
            jr.request_status
        FROM join_requests jr
        JOIN projects p ON jr.project_id = p.project_id
        JOIN students s ON jr.sender_student_id = s.student_id
        WHERE jr.receiver_student_id = %s
          AND jr.request_status = 'PENDING'
        ORDER BY jr.requested_at DESC
    """
    pending_received = fetch_all(sql_pending, (student_id,))

    # ------------------------------------------------------------------
    # My projects (created OR team member) — use project_details_view for title/domain
    # ------------------------------------------------------------------
    sql_my_projects = """
        SELECT
            p.project_id,
            pdv.project_title,
            pdv.domain,
            p.difficulty_level,
            pdv.deadline,
            pdv.project_status,
            p.max_team_size,
            p.current_team_size,
            p.created_by,
            CASE
                WHEN p.created_by = %s THEN 'CREATOR'
                ELSE (
                    SELECT tm.member_role
                    FROM teams t
                    JOIN team_members tm ON tm.team_id = t.team_id
                    WHERE t.project_id = p.project_id
                      AND tm.student_id = %s
                      AND tm.member_status = 'ACTIVE'
                    LIMIT 1
                )
            END AS role
        FROM projects p
        JOIN project_details_view pdv ON pdv.project_id = p.project_id
        WHERE p.project_id IN (
            SELECT project_id FROM projects WHERE created_by = %s
            UNION
            SELECT t.project_id
            FROM teams t
            JOIN team_members tm ON tm.team_id = t.team_id
            WHERE tm.student_id = %s
              AND tm.member_status = 'ACTIVE'
        )
        ORDER BY p.deadline
    """
    params_my = (student_id, student_id, student_id, student_id)
    my_projects_raw = fetch_all(sql_my_projects, params_my)

    my_projects = [
        {
            "project_id": row["project_id"],
            "project_title": row["project_title"],
            "domain": row["domain"],
            "role": row["role"] or "OTHER",
            "current_team_size": row["current_team_size"],
            "max_team_size": row["max_team_size"],
            "project_status": row["project_status"],
            "deadline": row["deadline"],
        }
        for row in my_projects_raw
    ]

    # ------------------------------------------------------------------
    # Sent requests
    # ------------------------------------------------------------------
    sql_sent = """
        SELECT
            jr.request_id,
            jr.project_id,
            p.project_title,
            jr.receiver_student_id,
            CONCAT(s.first_name, ' ', s.last_name) AS receiver_name,
            jr.message,
            jr.request_status,
            jr.requested_at,
            jr.responded_at
        FROM join_requests jr
        JOIN projects p ON jr.project_id = p.project_id
        JOIN students s ON jr.receiver_student_id = s.student_id
        WHERE jr.sender_student_id = %s
        ORDER BY jr.requested_at DESC
    """
    sent_requests = fetch_all(sql_sent, (student_id,))

    # ------------------------------------------------------------------
    # Top 3 OPEN matches from project_match_view (not already on team)
    # ------------------------------------------------------------------
    sql_top = """
        SELECT
            pmv.project_id,
            pmv.match_percentage,
            p.project_title,
            p.domain,
            p.difficulty_level,
            p.deadline,
            p.project_status
        FROM project_match_view pmv
        JOIN projects p ON p.project_id = pmv.project_id
        WHERE pmv.student_id = %s
          AND p.project_status = 'OPEN'
          AND p.created_by <> %s
          AND pmv.project_id NOT IN (
              SELECT t.project_id
              FROM teams t
              JOIN team_members tm ON tm.team_id = t.team_id
              WHERE tm.student_id = %s
                AND tm.member_status = 'ACTIVE'
          )
        ORDER BY pmv.match_percentage DESC, pmv.project_id
        LIMIT 3
    """
    top_raw = fetch_all(sql_top, (student_id, student_id, student_id))

    top_matches = []
    for proj in top_raw:
        sql_req = """
            SELECT
                sk.skill_id,
                sk.skill_name,
                prs.importance_weight,
                prs.minimum_proficiency
            FROM project_required_skills prs
            JOIN skills sk ON sk.skill_id = prs.skill_id
            WHERE prs.project_id = %s
        """
        required = fetch_all(sql_req, (proj["project_id"],))
        missing = [
            {
                "skill_id": r["skill_id"],
                "skill_name": r["skill_name"],
                "importance_weight": r["importance_weight"],
                "minimum_proficiency": r["minimum_proficiency"],
            }
            for r in required
            if r["skill_id"] not in skill_map
            or _rank(skill_map[r["skill_id"]]) < _rank(r["minimum_proficiency"])
        ]
        top_matches.append({
            **proj,
            "missing_skills": missing,
        })

    # ------------------------------------------------------------------
    # Skill gap (Python recompute) — top 3 lacking skills
    # ------------------------------------------------------------------
    sql_all_skills = """
        SELECT skill_id, skill_name FROM skills ORDER BY skill_name
    """
    all_skills = fetch_all(sql_all_skills)

    sql_open_reqs = """
        SELECT
            p.project_id,
            p.project_title,
            prs.skill_id,
            prs.importance_weight,
            prs.minimum_proficiency
        FROM projects p
        JOIN project_required_skills prs ON prs.project_id = p.project_id
        WHERE p.project_status = 'OPEN'
    """
    open_reqs = fetch_all(sql_open_reqs)

    # Group required skills by project (+ keep title)
    by_project = {}
    project_titles = {}
    for row in open_reqs:
        by_project.setdefault(row["project_id"], []).append(row)
        project_titles[row["project_id"]] = row["project_title"]

    lacking = [sk for sk in all_skills if sk["skill_id"] not in skill_map]
    gap_rows = []
    for sk in lacking:
        sid = sk["skill_id"]
        needing = [pid for pid, reqs in by_project.items() if any(r["skill_id"] == sid for r in reqs)]
        if not needing:
            continue

        sim_map = dict(skill_map)
        sim_map[sid] = "ADVANCED"

        best = 0.0
        best_pid = None
        for pid in needing:
            pct = _match_percent(by_project[pid], sim_map)
            if pct > best:
                best = pct
                best_pid = pid

        gap_rows.append({
            "skill_id": sid,
            "skill_name": sk["skill_name"],
            "open_projects_needing": len(needing),
            "best_match_percent_if_added": best,
            "best_project_id": best_pid,
            "best_project_title": project_titles.get(best_pid),
        })

    gap_rows.sort(
        key=lambda r: (r["best_match_percent_if_added"], r["open_projects_needing"]),
        reverse=True,
    )
    skill_gap = gap_rows[:3]
    return jsonify({
        "student_id": student_id,
        "profile": {
            "first_name": profile["first_name"],
            "last_name": profile["last_name"],
            "email": profile["email"],
        },
        "profile_strength": profile_strength,
        "pending_received": pending_received,
        "my_projects": my_projects,
        "sent_requests": sent_requests,
        "top_matches": top_matches,
        "skill_gap": skill_gap,
    })


def _profile_data(student_id):
    """Read the student's editable profile fields and skill list."""
    profile_sql = """
        SELECT
            s.student_id, s.first_name, s.last_name, s.email, s.bio,
            s.github_portfolio, s.college, s.year_of_study, s.department_id,
            d.department_name, s.experience_level, s.availability_status
        FROM students s
        LEFT JOIN departments d ON d.department_id = s.department_id
        WHERE s.student_id = %s
    """
    skills_sql = """
        SELECT
            sk.skill_id, sk.skill_name, sk.skill_category,
            ss.proficiency_level, ss.years_of_experience, ss.is_verified
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = %s
        ORDER BY sk.skill_category, sk.skill_name
    """
    profile = fetch_one(profile_sql, (student_id,))
    if not profile:
        return None
    profile["skills"] = fetch_all(skills_sql, (student_id,))
    return profile


def _validated_years(value):
    """Parse experience as a decimal number from 0 through 20."""
    try:
        years = Decimal(str(value))
        if not years.is_finite() or years < 0 or years > 20:
            return None
        return years
    except (TypeError, ValueError, InvalidOperation):
        return None


def _valid_proficiency(value):
    level = str(value or "").upper()
    return level if level in PROF_RANK else None


@me_bp.get("/me/profile")
@login_required
def get_my_profile():
    """Return the logged-in student's own profile and skills."""
    profile = _profile_data(g.student_id)
    if not profile:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(profile)


@me_bp.put("/me/profile")
@login_required
def update_my_profile():
    """Update only the profile fields listed in this endpoint's allow-list."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Profile fields must be sent as an object"}), 400

    allowed = {
        "bio": "bio",
        "github_portfolio": "github_portfolio",
        "college": "college",
        "year_of_study": "year_of_study",
        "department_id": "department_id",
        "experience_level": "experience_level",
        "availability_status": "availability_status",
    }
    updates = {}
    limits = {"bio": 500, "github_portfolio": 255, "college": 150}
    for field, limit in limits.items():
        if field in data:
            value = data[field]
            if value is not None and not isinstance(value, str):
                return jsonify({"error": f"{field} must be text"}), 400
            clean = (value or "").strip()
            if len(clean) > limit:
                return jsonify({"error": f"{field} must be {limit} characters or fewer"}), 400
            updates[field] = clean or None

    if "year_of_study" in data:
        try:
            raw_year = data["year_of_study"]
            year_number = Decimal(str(raw_year))
            if isinstance(raw_year, bool) or not year_number.is_finite() or year_number != year_number.to_integral_value():
                raise ValueError()
            year = int(year_number)
        except (TypeError, ValueError, InvalidOperation):
            return jsonify({"error": "Year of study must be between 1 and 4"}), 400
        if not 1 <= year <= 4:
            return jsonify({"error": "Year of study must be between 1 and 4"}), 400
        updates["year_of_study"] = year

    if "department_id" in data:
        try:
            raw_department_id = data["department_id"]
            department_number = Decimal(str(raw_department_id))
            if isinstance(raw_department_id, bool) or not department_number.is_finite() or department_number != department_number.to_integral_value():
                raise ValueError()
            department_id = int(department_number)
        except (TypeError, ValueError, InvalidOperation):
            return jsonify({"error": "Choose a valid department"}), 400
        department_sql = "SELECT department_id FROM departments WHERE department_id = %s"
        if not fetch_one(department_sql, (department_id,)):
            return jsonify({"error": "Department not found"}), 400
        updates["department_id"] = department_id

    enum_values = {
        "experience_level": {"BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"},
        "availability_status": {"AVAILABLE", "PARTIALLY_AVAILABLE", "NOT_AVAILABLE"},
    }
    for field, allowed_values in enum_values.items():
        if field in data:
            value = str(data[field] or "").upper()
            if value not in allowed_values:
                return jsonify({"error": f"Choose a valid {field.replace('_', ' ')}"}), 400
            updates[field] = value

    if not updates:
        return jsonify({"error": "Send at least one profile field to update"}), 400

    # Column names come only from the fixed allow-list above.
    assignments = [f"{allowed[field]} = %s" for field in updates]
    sql = f"UPDATE students SET {', '.join(assignments)} WHERE student_id = %s"
    params = tuple(updates.values()) + (g.student_id,)
    try:
        execute_write(sql, params)
    except mysql.connector.Error as err:
        return jsonify({"error": err.msg}), 400

    profile = _profile_data(g.student_id)
    if not profile:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(profile)


@me_bp.post("/me/skills")
@login_required
def add_my_skill():
    """Add a skill to the logged-in student's profile."""
    data = request.get_json(silent=True) or {}
    try:
        skill_id = int(data.get("skill_id"))
    except (TypeError, ValueError, AttributeError):
        return jsonify({"error": "Choose a valid skill"}), 400
    proficiency = _valid_proficiency(data.get("proficiency_level"))
    years = _validated_years(data.get("years_of_experience", 0))
    if not proficiency:
        return jsonify({"error": "Choose a valid proficiency level"}), 400
    if years is None:
        return jsonify({"error": "Years of experience must be between 0 and 20"}), 400

    skill_sql = "SELECT skill_id FROM skills WHERE skill_id = %s"
    if not fetch_one(skill_sql, (skill_id,)):
        return jsonify({"error": "Skill not found"}), 404
    insert_sql = """
        INSERT INTO student_skills
            (student_id, skill_id, proficiency_level, years_of_experience)
        VALUES (%s, %s, %s, %s)
    """
    params = (g.student_id, skill_id, proficiency, years)
    try:
        execute_write(insert_sql, params)
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({"error": "You already have this skill"}), 400
        return jsonify({"error": err.msg}), 400

    read_sql = """
        SELECT sk.skill_id, sk.skill_name, sk.skill_category,
               ss.proficiency_level, ss.years_of_experience, ss.is_verified
        FROM student_skills ss JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = %s AND ss.skill_id = %s
    """
    skill = fetch_one(read_sql, (g.student_id, skill_id))
    return jsonify({
        "skill": skill,
    }), 201


@me_bp.put("/me/skills/<int:skill_id>")
@login_required
def update_my_skill(skill_id):
    """Update proficiency and/or experience for one of the student's skills."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Skill fields must be sent as an object"}), 400
    own_sql = "SELECT proficiency_level FROM student_skills WHERE student_id = %s AND skill_id = %s"
    owned = fetch_one(own_sql, (g.student_id, skill_id))
    if not owned:
        return jsonify({"error": "You do not have this skill"}), 404

    updates = {}
    if "proficiency_level" in data:
        level = _valid_proficiency(data["proficiency_level"])
        if not level:
            return jsonify({"error": "Choose a valid proficiency level"}), 400
        updates["proficiency_level"] = level
    if "years_of_experience" in data:
        years = _validated_years(data["years_of_experience"])
        if years is None:
            return jsonify({"error": "Years of experience must be between 0 and 20"}), 400
        updates["years_of_experience"] = years
    if not updates:
        return jsonify({"error": "Send proficiency_level or years_of_experience"}), 400
    if updates.get("proficiency_level", owned["proficiency_level"]) != owned["proficiency_level"]:
        updates["is_verified"] = False

    assignments = [f"{field} = %s" for field in updates]
    sql = f"UPDATE student_skills SET {', '.join(assignments)} WHERE student_id = %s AND skill_id = %s"
    params = tuple(updates.values()) + (g.student_id, skill_id)
    try:
        execute_write(sql, params)
    except mysql.connector.Error as err:
        return jsonify({"error": err.msg}), 400
    read_sql = """
        SELECT sk.skill_id, sk.skill_name, sk.skill_category,
               ss.proficiency_level, ss.years_of_experience, ss.is_verified
        FROM student_skills ss JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = %s AND ss.skill_id = %s
    """
    skill = fetch_one(read_sql, (g.student_id, skill_id))
    return jsonify({
        "skill": skill,
    })


@me_bp.delete("/me/skills/<int:skill_id>")
@login_required
def delete_my_skill(skill_id):
    """Remove only the logged-in student's skill row."""
    own_sql = "SELECT student_skill_id FROM student_skills WHERE student_id = %s AND skill_id = %s"
    if not fetch_one(own_sql, (g.student_id, skill_id)):
        return jsonify({"error": "You do not have this skill"}), 404
    sql = "DELETE FROM student_skills WHERE student_id = %s AND skill_id = %s"
    params = (g.student_id, skill_id)
    try:
        affected, _ = execute_write(sql, params)
    except mysql.connector.Error as err:
        return jsonify({"error": err.msg}), 400
    if not affected:
        return jsonify({"error": "You do not have this skill"}), 404
    return jsonify({
        "deleted": skill_id,
    })


@me_bp.put("/me/password")
@login_required
def change_my_password():
    """Verify the current password before saving a new password hash."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Password fields must be sent as an object"}), 400
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    if not isinstance(current_password, str) or not isinstance(new_password, str):
        return jsonify({"error": "Passwords must be text"}), 400
    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    sql_current = "SELECT password_hash FROM students WHERE student_id = %s"
    row = fetch_one(sql_current, (g.student_id,))
    if not row:
        return jsonify({"error": "Student not found"}), 404
    if not check_password_hash(row["password_hash"], current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    password_hash = generate_password_hash(new_password)
    sql_update = "UPDATE students SET password_hash = %s WHERE student_id = %s"
    params = (password_hash, g.student_id)
    try:
        execute_write(sql_update, params)
    except mysql.connector.Error as err:
        return jsonify({"error": err.msg}), 400
    return jsonify({
        "message": "Password updated",
    })
