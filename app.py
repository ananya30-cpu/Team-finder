"""
College Project Team Finder — Flask API

Run from the backend folder:
    pip install -r requirements.txt
    flask --app app run --debug --port 5000
"""

from flask import Flask, jsonify
from flask_cors import CORS

from routes.students import students_bp
from routes.projects import projects_bp
from routes.join_requests import join_requests_bp
from routes.stats import stats_bp
from routes.connections import connections_bp
from routes.meta import meta_bp
from routes.auth import auth_bp
from routes.me import me_bp


def create_app():
    """Build and configure the Flask application."""
    app = Flask(__name__)

    # Allow the React frontend (Vite) to call this API from another port
    CORS(app)

    # Register route blueprints under /api/...
    app.register_blueprint(students_bp, url_prefix="/api")
    app.register_blueprint(projects_bp, url_prefix="/api")
    app.register_blueprint(join_requests_bp, url_prefix="/api")
    app.register_blueprint(stats_bp, url_prefix="/api")
    app.register_blueprint(connections_bp, url_prefix="/api")
    app.register_blueprint(meta_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(me_bp, url_prefix="/api")

    @app.get("/")
    def index():
        """Explain where to open the frontend and check the API."""
        return jsonify({
            "name": "College Project Team Finder API",
            "status": "ok",
            "frontend": "http://localhost:5173",
            "api_base": "/api",
            "health": "/api/health",
        })

    @app.get("/api")
    def api_index():
        """Give a helpful response when someone opens the API base URL."""
        return jsonify({
            "name": "College Project Team Finder API",
            "status": "ok",
            "health": "/api/health",
        })

    @app.get("/api/health")
    def health():
        """Simple check that the server is up (public — no auth)."""
        return jsonify({"status": "ok"})

    # Consistent JSON error shape for uncaught errors
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


# Used by: flask --app app run
app = create_app()


if __name__ == "__main__":
    # Direct run: python app.py
    app.run(debug=True, port=5000)
