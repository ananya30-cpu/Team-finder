"""
Project endpoints (all require login).
Match % always uses the logged-in student from the JWT.
"""

from datetime import date, datetime

from flask import Blueprint, jsonify, request, g
import mysql.connector

from db import fetch_all, fetch_one, get_connection, proficiency_to_int
from auth import login_required

projects_bp = Blueprint("projects", __name__)


def _required_skills(project_id):
    """Skills required by a project, with weight and minimum proficiency."""
    return fetch_all(
        """
        SELECT
            sk.skill_id,
            sk.skill_name,
            prs.importance_weight,
            prs.minimum_proficiency
        FROM project_required_skills prs
        JOIN skills sk ON prs.skill_id = sk.skill_id
        WHERE prs.project_id = %s
        ORDER BY prs.importance_weight DESC
        """,
        (project_id,),
    )


def _match_percentage(student_id, project_id):
    """Read precomputed match from project_match_view (0 if no student)."""
    if not student_id:
        return None
    row = fetch_one(
        """
        SELECT match_percentage
        FROM project_match_view
        WHERE student_id = %s AND project_id = %s
        """,
        (student_id, project_id),
    )
    return row["match_percentage"] if row else 0.0


def _matched_and_missing(student_id, required):
    """
    Split required skills into matched vs missing for one student.
    Matched = student has the skill at proficiency >= minimum.
    """
    if not student_id or not required:
        return [], list(required)

    student_skills = fetch_all(
        """
        SELECT skill_id, proficiency_level
        FROM student_skills
        WHERE student_id = %s
        """,
        (student_id,),
    )
    by_id = {s["skill_id"]: s for s in student_skills}

    matched = []
    missing = []
    for req in required:
        ss = by_id.get(req["skill_id"])
        if ss and proficiency_to_int(ss["proficiency_level"]) >= proficiency_to_int(
            req["minimum_proficiency"]
        ):
            matched.append({**req, "student_proficiency": ss["proficiency_level"]})
        else:
            missing.append(req)
    return matched, missing


def _project_base_row(p, student_id=None):
    """Attach required skills, match %, matched/missing, days_left to a project dict."""
    required = _required_skills(p["project_id"])
    matched, missing = _matched_and_missing(student_id, required) if student_id else ([], required)

    return {
        **p,
        "required_skills": required,
        "match_percentage": _match_percentage(student_id, p["project_id"]),
        "matched_skills": matched if student_id else [],
        "missing_skills": missing if student_id else required,
    }


@projects_bp.get("/projects")
@login_required
def list_projects():
    """List all projects with match % for the logged-in student."""
    student_id = g.student_id

    projects = fetch_all(
        """
        SELECT
            p.project_id,
            p.project_title,
            p.project_description,
            p.domain,
            p.difficulty_level,
            p.deadline,
            p.max_team_size,
            p.current_team_size,
            p.project_status,
            p.created_by,
            CONCAT(s.first_name, ' ', s.last_name) AS creator_name,
            DATEDIFF(p.deadline, CURDATE()) AS days_left
        FROM projects p
        JOIN students s ON p.created_by = s.student_id
        WHERE p.project_status <> 'CANCELLED'
        ORDER BY p.created_at DESC
        """
    )

    result = [_project_base_row(p, student_id) for p in projects]
    return jsonify(result)


@projects_bp.post("/projects")
@login_required
def create_project():
    """Create a project, its required skills, and the creator's team membership."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Project details must be sent as an object"}), 400
    title = data.get("project_title")
    description = data.get("project_description")
    domain = data.get("domain")
    if not all(isinstance(value, str) for value in (title, description, domain)):
        return jsonify({"error": "Title, description, and domain are required"}), 400
    title = title.strip()
    description = description.strip()
    domain = domain.strip()
    difficulty = str(data.get("difficulty_level", "")).upper()
    deadline_text = str(data.get("deadline", "")).strip()
    skills = data.get("skills")

    if not title or len(title) > 200:
        return jsonify({"error": "Title is required and must be 200 characters or fewer"}), 400
    if not description or len(description) > 2000:
        return jsonify({"error": "Description is required and must be 2000 characters or fewer"}), 400
    if not domain or len(domain) > 100:
        return jsonify({"error": "Domain is required and must be 100 characters or fewer"}), 400
    if difficulty not in {"EASY", "MEDIUM", "HARD"}:
        return jsonify({"error": "Difficulty must be Easy, Medium, or Hard"}), 400

    try:
        raw_size = data.get("max_team_size")
        if isinstance(raw_size, bool) or int(raw_size) != float(raw_size):
            raise ValueError()
        max_team_size = int(raw_size)
        deadline = date.fromisoformat(deadline_text)
    except (TypeError, ValueError, OverflowError):
        return jsonify({"error": "A valid team size and deadline are required"}), 400
    if max_team_size < 2 or max_team_size > 10:
        return jsonify({"error": "Maximum team size must be between 2 and 10"}), 400
    if deadline <= date.today():
        return jsonify({"error": "Deadline must be a future date"}), 400
    if not isinstance(skills, list) or not 1 <= len(skills) <= 10:
        return jsonify({"error": "Choose between 1 and 10 required skills"}), 400

    normalized_skills = []
    seen_skill_ids = set()
    for skill in skills:
        try:
            raw_skill_id = skill.get("skill_id")
            raw_weight = skill.get("importance_weight")
            if isinstance(raw_skill_id, bool) or int(raw_skill_id) != float(raw_skill_id):
                raise ValueError()
            if isinstance(raw_weight, bool) or int(raw_weight) != float(raw_weight):
                raise ValueError()
            skill_id = int(raw_skill_id)
            weight = int(raw_weight)
        except (AttributeError, TypeError, ValueError, OverflowError):
            return jsonify({"error": "Each skill needs a valid id and importance weight"}), 400
        proficiency = str(skill.get("minimum_proficiency", "")).upper()
        if skill_id in seen_skill_ids:
            return jsonify({"error": "Each required skill can only be selected once"}), 400
        if not 1 <= weight <= 10:
            return jsonify({"error": "Skill importance must be between 1 and 10"}), 400
        if proficiency not in {"BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"}:
            return jsonify({"error": "Choose a valid minimum proficiency for every skill"}), 400
        seen_skill_ids.add(skill_id)
        normalized_skills.append((skill_id, weight, proficiency))

    student_id = g.student_id
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        placeholders = ", ".join(["%s"] * len(normalized_skills))
        cursor.execute(
            f"SELECT skill_id FROM skills WHERE skill_id IN ({placeholders})",
            tuple(item[0] for item in normalized_skills),
        )
        found_skill_ids = {row["skill_id"] for row in cursor.fetchall()}
        if found_skill_ids != seen_skill_ids:
            connection.rollback()
            return jsonify({"error": "One or more selected skills are no longer available"}), 400

        insert_project = """
            INSERT INTO projects
                (created_by, project_title, project_description, domain,
                 max_team_size, current_team_size, difficulty_level, deadline, project_status)
            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s)
        """
        project_params = (
            student_id, title, description, domain, max_team_size, difficulty, deadline, "OPEN",
        )
        cursor.execute(insert_project, project_params)
        project_id = cursor.lastrowid

        insert_skill = """
            INSERT INTO project_required_skills
                (project_id, skill_id, importance_weight, minimum_proficiency)
            VALUES (%s, %s, %s, %s)
        """
        for skill_id, weight, proficiency in normalized_skills:
            skill_params = (project_id, skill_id, weight, proficiency)
            cursor.execute(insert_skill, skill_params)

        insert_team = """
            INSERT INTO teams
                (project_id, team_name, team_leader_id, max_members)
            VALUES (%s, %s, %s, %s)
        """
        team_params = (project_id, f"{title} Team", student_id, max_team_size)
        cursor.execute(insert_team, team_params)
        team_id = cursor.lastrowid

        insert_member = """
            INSERT INTO team_members (team_id, student_id, member_role, member_status)
            VALUES (%s, %s, %s, %s)
        """
        member_params = (team_id, student_id, "LEADER", "ACTIVE")
        cursor.execute(insert_member, member_params)

        # Build the GET /projects/<id> response before committing, on this connection.
        cursor.execute(
            """
            SELECT p.project_id, p.project_title, p.project_description, p.domain,
                   p.difficulty_level, DATE_FORMAT(p.deadline, '%Y-%m-%d') AS deadline,
                   p.max_team_size, p.current_team_size, p.project_status, p.created_by,
                   CONCAT(s.first_name, ' ', s.last_name) AS creator_name,
                   DATEDIFF(p.deadline, CURDATE()) AS days_left
            FROM projects p JOIN students s ON p.created_by = s.student_id
            WHERE p.project_id = %s
            """,
            (project_id,),
        )
        project = cursor.fetchone()

        cursor.execute(
            """
            SELECT sk.skill_id, sk.skill_name, prs.importance_weight, prs.minimum_proficiency
            FROM project_required_skills prs JOIN skills sk ON prs.skill_id = sk.skill_id
            WHERE prs.project_id = %s
            ORDER BY prs.importance_weight DESC
            """,
            (project_id,),
        )
        required = cursor.fetchall()

        cursor.execute(
            "SELECT skill_id, proficiency_level FROM student_skills WHERE student_id = %s",
            (student_id,),
        )
        own_skills = {row["skill_id"]: row["proficiency_level"] for row in cursor.fetchall()}
        matched = []
        missing = []
        for required_skill in required:
            own_level = own_skills.get(required_skill["skill_id"])
            if own_level and proficiency_to_int(own_level) >= proficiency_to_int(required_skill["minimum_proficiency"]):
                matched.append({**required_skill, "student_proficiency": own_level})
            else:
                missing.append(required_skill)

        cursor.execute(
            "SELECT match_percentage FROM project_match_view WHERE student_id = %s AND project_id = %s",
            (student_id, project_id),
        )
        match_row = cursor.fetchone()
        project["match_percentage"] = float(match_row["match_percentage"]) if match_row else 0.0
        project["required_skills"] = required
        project["matched_skills"] = matched
        project["missing_skills"] = missing

        cursor.execute(
            """
            SELECT tm.team_member_id, tm.student_id,
                   CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                   tm.member_role, tm.member_status, tm.joined_at,
                   t.team_id, t.team_name
            FROM teams t JOIN team_members tm ON t.team_id = tm.team_id
            JOIN students s ON tm.student_id = s.student_id
            WHERE t.project_id = %s AND tm.member_status = 'ACTIVE'
            ORDER BY tm.joined_at
            """,
            (project_id,),
        )
        project["team_members"] = cursor.fetchall()
        for member in project["team_members"]:
            if isinstance(member["joined_at"], datetime):
                member["joined_at"] = member["joined_at"].isoformat(sep=" ", timespec="seconds")
        connection.commit()
    except mysql.connector.Error as err:
        connection.rollback()
        return jsonify({"error": err.msg}), 400
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

    return jsonify(project), 201


@projects_bp.patch("/projects/<int:project_id>/status")
@login_required
def update_project_status(project_id):
    """Let only the project creator move it to CANCELLED or IN_PROGRESS."""
    data = request.get_json(silent=True) or {}
    requested_status = str(data.get("project_status", "")).upper()
    connection = get_connection()
    cursor = connection.cursor()
    sql_project = "SELECT created_by, project_status FROM projects WHERE project_id = %s FOR UPDATE"
    try:
        cursor.execute(sql_project, (project_id,))
        project = cursor.fetchone()
        if not project:
            connection.rollback()
            return jsonify({"error": "Project not found"}), 404

        created_by, current_status = project
        if int(created_by) != int(g.student_id):
            connection.rollback()
            return jsonify({"error": "Only the project creator can change its status"}), 403
        if requested_status not in {"CANCELLED", "IN_PROGRESS"}:
            connection.rollback()
            return jsonify({"error": "Status must be CANCELLED or IN_PROGRESS"}), 400
        if current_status == "COMPLETED":
            connection.rollback()
            return jsonify({"error": "Completed projects cannot be changed"}), 400

        sql_update = "UPDATE projects SET project_status = %s WHERE project_id = %s"
        params_update = (requested_status, project_id)
        cursor.execute(sql_update, params_update)
        connection.commit()
    except mysql.connector.Error as err:
        connection.rollback()
        return jsonify({"error": err.msg}), 400
    finally:
        cursor.close()
        connection.close()

    return jsonify({
        "project_id": project_id,
        "project_status": requested_status,
    })


@projects_bp.get("/projects/<int:project_id>")
@login_required
def get_project(project_id):
    """One project + team members; match % for the logged-in student."""
    student_id = g.student_id

    project = fetch_one(
        """
        SELECT
            p.project_id,
            p.project_title,
            p.project_description,
            p.domain,
            p.difficulty_level,
            p.deadline,
            p.max_team_size,
            p.current_team_size,
            p.project_status,
            p.created_by,
            CONCAT(s.first_name, ' ', s.last_name) AS creator_name,
            DATEDIFF(p.deadline, CURDATE()) AS days_left
        FROM projects p
        JOIN students s ON p.created_by = s.student_id
        WHERE p.project_id = %s
        """,
        (project_id,),
    )
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = _project_base_row(project, student_id)

    # Team members with roles (via teams → team_members)
    members = fetch_all(
        """
        SELECT
            tm.team_member_id,
            tm.student_id,
            CONCAT(s.first_name, ' ', s.last_name) AS student_name,
            tm.member_role,
            tm.member_status,
            tm.joined_at,
            t.team_id,
            t.team_name
        FROM teams t
        JOIN team_members tm ON t.team_id = tm.team_id
        JOIN students s ON tm.student_id = s.student_id
        WHERE t.project_id = %s
          AND tm.member_status = 'ACTIVE'
        ORDER BY tm.joined_at
        """,
        (project_id,),
    )
    data["team_members"] = members
    return jsonify(data)


def _team_member_ids(project_id):
    """Set of student_ids already on this project's team."""
    rows = fetch_all(
        """
        SELECT tm.student_id
        FROM teams t
        JOIN team_members tm ON t.team_id = tm.team_id
        WHERE t.project_id = %s AND tm.member_status = 'ACTIVE'
        """,
        (project_id,),
    )
    return {r["student_id"] for r in rows}


def _student_skill_map(student_ids):
    """
    Map student_id → {skill_id: proficiency_int}
    for a list of candidates (one query).
    """
    if not student_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(student_ids))
    rows = fetch_all(
        f"""
        SELECT student_id, skill_id, proficiency_level
        FROM student_skills
        WHERE student_id IN ({placeholders})
        """,
        tuple(student_ids),
    )
    result = {}
    for r in rows:
        sid = r["student_id"]
        result.setdefault(sid, {})[r["skill_id"]] = proficiency_to_int(r["proficiency_level"])
    return result


def _coverage_weight(skill_map, required_list, covered_skill_ids):
    """
    Total importance_weight of required skills that are covered
    (either already covered or present in skill_map at min proficiency).
    """
    total = 0
    for req in required_list:
        sid = req["skill_id"]
        if sid in covered_skill_ids:
            total += req["importance_weight"]
            continue
        if skill_map.get(sid, 0) >= proficiency_to_int(req["minimum_proficiency"]):
            total += req["importance_weight"]
    return total


def _uncovered_required(required_list, member_skill_maps):
    """
    Required skills not yet met by ANY current team member
    at the minimum proficiency.
    Returns list of required-skill dicts still uncovered.
    """
    uncovered = []
    for req in required_list:
        min_rank = proficiency_to_int(req["minimum_proficiency"])
        covered = False
        for smap in member_skill_maps:
            if smap.get(req["skill_id"], 0) >= min_rank:
                covered = True
                break
        if not covered:
            uncovered.append(req)
    return uncovered


@projects_bp.post("/projects/<int:project_id>/dream-team")
@login_required
def dream_team(project_id):
    """
    Greedy dream-team builder.
    ?size=N — how many new members to pick (default 3).

    Each step picks the AVAILABLE / PARTIALLY_AVAILABLE student (not already
    on the team) who covers the most still-uncovered required-skill weight.
    """
    size = request.args.get("size", default=3, type=int)
    if size < 1:
        return jsonify({"error": "size must be at least 1"}), 400

    project = fetch_one(
        "SELECT project_id, project_title, max_team_size FROM projects WHERE project_id = %s",
        (project_id,),
    )
    if not project:
        return jsonify({"error": "Project not found"}), 404

    required = _required_skills(project_id)
    if not required:
        return jsonify({
            "project_id": project_id,
            "picks": [],
            "final_coverage_percent": 0.0,
            "message": "Project has no required skills",
        })

    total_weight = sum(r["importance_weight"] for r in required)

    # Skills already covered by the current team
    already_on_team = _team_member_ids(project_id)
    member_maps = list(_student_skill_map(list(already_on_team)).values())
    covered = set()
    for req in required:
        min_rank = proficiency_to_int(req["minimum_proficiency"])
        for smap in member_maps:
            if smap.get(req["skill_id"], 0) >= min_rank:
                covered.add(req["skill_id"])
                break

    # Candidate pool
    candidates = fetch_all(
        """
        SELECT student_id, first_name, last_name, availability_status, experience_level
        FROM students
        WHERE account_status = 'ACTIVE'
          AND availability_status IN ('AVAILABLE', 'PARTIALLY_AVAILABLE')
        """
    )
    candidates = [c for c in candidates if c["student_id"] not in already_on_team]
    cand_skills = _student_skill_map([c["student_id"] for c in candidates])

    picks = []
    remaining = list(candidates)

    for _ in range(size):
        if not remaining:
            break

        best = None
        best_gain = -1
        best_new_skills = []

        for cand in remaining:
            smap = cand_skills.get(cand["student_id"], {})
            newly = []
            gain = 0
            for req in required:
                if req["skill_id"] in covered:
                    continue
                if smap.get(req["skill_id"], 0) >= proficiency_to_int(req["minimum_proficiency"]):
                    gain += req["importance_weight"]
                    newly.append({
                        "skill_id": req["skill_id"],
                        "skill_name": req["skill_name"],
                        "importance_weight": req["importance_weight"],
                    })
            if gain > best_gain:
                best_gain = gain
                best = cand
                best_new_skills = newly

        # Stop if nobody covers anything new
        if best is None or best_gain <= 0:
            break

        for sk in best_new_skills:
            covered.add(sk["skill_id"])

        picks.append({
            "student_id": best["student_id"],
            "name": f"{best['first_name']} {best['last_name']}",
            "availability_status": best["availability_status"],
            "experience_level": best["experience_level"],
            "weight_gained": best_gain,
            "newly_covered_skills": best_new_skills,
        })
        remaining = [c for c in remaining if c["student_id"] != best["student_id"]]

    covered_weight = sum(
        r["importance_weight"] for r in required if r["skill_id"] in covered
    )
    final_pct = round((covered_weight / total_weight) * 100, 1) if total_weight else 0.0

    return jsonify({
        "project_id": project_id,
        "project_title": project["project_title"],
        "requested_size": size,
        "picks": picks,
        "final_coverage_percent": final_pct,
        "covered_weight": covered_weight,
        "total_required_weight": total_weight,
    })


@projects_bp.get("/projects/<int:project_id>/recruit-suggestions")
@login_required
def recruit_suggestions(project_id):
    """
    Uncovered required skills of the current team, plus best-fit students
    for each uncovered skill (and an overall ranking).
    """
    project = fetch_one(
        "SELECT project_id, project_title FROM projects WHERE project_id = %s",
        (project_id,),
    )
    if not project:
        return jsonify({"error": "Project not found"}), 404

    required = _required_skills(project_id)
    already_on_team = _team_member_ids(project_id)
    member_maps = list(_student_skill_map(list(already_on_team)).values())
    uncovered = _uncovered_required(required, member_maps)

    # Candidates not on the team
    candidates = fetch_all(
        """
        SELECT student_id, first_name, last_name, availability_status, experience_level
        FROM students
        WHERE account_status = 'ACTIVE'
          AND availability_status IN ('AVAILABLE', 'PARTIALLY_AVAILABLE')
        """
    )
    candidates = [c for c in candidates if c["student_id"] not in already_on_team]
    cand_skills = _student_skill_map([c["student_id"] for c in candidates])

    # Per uncovered skill: students who meet the minimum
    by_skill = []
    for req in uncovered:
        min_rank = proficiency_to_int(req["minimum_proficiency"])
        fits = []
        for cand in candidates:
            rank = cand_skills.get(cand["student_id"], {}).get(req["skill_id"], 0)
            if rank >= min_rank:
                fits.append({
                    "student_id": cand["student_id"],
                    "name": f"{cand['first_name']} {cand['last_name']}",
                    "proficiency_rank": rank,
                    "availability_status": cand["availability_status"],
                })
        fits.sort(key=lambda x: -x["proficiency_rank"])
        by_skill.append({
            "skill_id": req["skill_id"],
            "skill_name": req["skill_name"],
            "importance_weight": req["importance_weight"],
            "minimum_proficiency": req["minimum_proficiency"],
            "suggested_students": fits[:5],
        })

    # Overall: students ranked by how much uncovered weight they cover
    overall = []
    for cand in candidates:
        smap = cand_skills.get(cand["student_id"], {})
        gain = 0
        covers = []
        for req in uncovered:
            if smap.get(req["skill_id"], 0) >= proficiency_to_int(req["minimum_proficiency"]):
                gain += req["importance_weight"]
                covers.append(req["skill_name"])
        if gain > 0:
            overall.append({
                "student_id": cand["student_id"],
                "name": f"{cand['first_name']} {cand['last_name']}",
                "availability_status": cand["availability_status"],
                "weight_covered": gain,
                "skills_covered": covers,
            })
    overall.sort(key=lambda x: -x["weight_covered"])

    return jsonify({
        "project_id": project_id,
        "project_title": project["project_title"],
        "uncovered_skills": [
            {
                "skill_id": u["skill_id"],
                "skill_name": u["skill_name"],
                "importance_weight": u["importance_weight"],
                "minimum_proficiency": u["minimum_proficiency"],
            }
            for u in uncovered
        ],
        "suggestions_by_skill": by_skill,
        "best_fit_students": overall[:10],
    })
