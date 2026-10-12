"""
Lookup lists:
  GET /api/departments  — public (register form)
  GET /api/skills       — public skill catalog for signup; harmless lookup data
"""

from flask import Blueprint, jsonify
from db import fetch_all

meta_bp = Blueprint("meta", __name__)


@meta_bp.get("/departments")
def list_departments():
    """Public — needed on the register form before login."""
    rows = fetch_all(
        """
        SELECT department_id, department_name, department_code
        FROM departments
        ORDER BY department_name
        """
    )
    return jsonify(rows)


@meta_bp.get("/skills")
def list_skills():
    rows = fetch_all(
        """
        SELECT skill_id, skill_name, skill_category, description
        FROM skills
        ORDER BY skill_name
        """
    )
    return jsonify(rows)
