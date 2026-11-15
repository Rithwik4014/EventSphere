# app/__init__.py
"""
EventSphere Flask Application Factory.
Configures Flask, PyMongo JSON serialization, Web views, Blueprints, and error handlers.
"""

import os
from datetime import datetime
from bson import ObjectId
from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider

from .config import config_by_name
from .services.db import get_client, get_db
from .routes import auth_bp, events_bp, bookings_bp, admin_bp, web_bp

class MongoJSONProvider(DefaultJSONProvider):
    """Custom Flask JSON Provider to serialize BSON ObjectId and datetime objects."""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def create_app(config_name=None):
    """Application factory for EventSphere."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Use MongoJSONProvider for automatic ObjectId and datetime serialization
    app.json_provider_class = MongoJSONProvider
    app.json = MongoJSONProvider(app)

    # Verify PyMongo connection
    with app.app_context():
        try:
            get_client()
        except Exception as e:
            app.logger.warning(f"Initial MongoDB connection deferred: {e}")

    # Register Blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(admin_bp)

    # Apply ProxyFix when in production or on Render (behind reverse proxy)
    if config_name == "production" or os.environ.get("RENDER"):
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        except Exception as e:
            app.logger.warning(f"Could not apply ProxyFix: {e}")

    # Healthcheck endpoint
    @app.route("/api/health", methods=["GET"])
    def health():
        try:
            db = get_db()
            db.command("ping")
            db_status = "connected"
        except Exception as e:
            db_status = f"disconnected ({str(e)})"

        return jsonify({
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error": "Bad request",
            "message": str(error)
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": "Resource not found"
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "success": False,
            "error": "Method not allowed"
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

    return app
