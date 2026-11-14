# app/routes/admin_routes.py
"""
Admin & Analytics Blueprint for EventSphere.
Serves aggregation analytics endpoints and management lists for events and users.
"""

from flask import Blueprint, request, jsonify
from app.services.analytics_service import AnalyticsService
from app.services.event_service import EventService
from app.services.user_service import UserService
from .auth_helpers import admin_required

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/admin")

@admin_bp.route("/analytics/summary", methods=["GET"])
@admin_required
def get_platform_summary():
    """Retrieve top-level platform overview KPIs."""
    kpis = AnalyticsService.get_platform_kpis()
    return jsonify({"success": True, "kpis": kpis}), 200

@admin_bp.route("/analytics/events", methods=["GET"])
@admin_required
def get_event_performance():
    """Retrieve event performance, tickets sold, and confirmed revenue per event."""
    summary = AnalyticsService.get_event_booking_summary()
    return jsonify({
        "success": True,
        "count": len(summary),
        "events": summary
    }), 200

@admin_bp.route("/analytics/categories", methods=["GET"])
@admin_required
def get_category_analytics():
    """Retrieve popularity, ticket sales, and revenue broken down by event category."""
    categories = AnalyticsService.get_most_popular_categories()
    return jsonify({
        "success": True,
        "count": len(categories),
        "categories": categories
    }), 200

@admin_bp.route("/analytics/monthly", methods=["GET"])
@admin_required
def get_monthly_trends():
    """Retrieve monthly ticket sales and revenue trends."""
    trends = AnalyticsService.get_monthly_booking_statistics()
    return jsonify({
        "success": True,
        "count": len(trends),
        "monthly_trends": trends
    }), 200

@admin_bp.route("/analytics/user-history", methods=["GET"])
@admin_required
def get_global_booking_history():
    """Retrieve global booking records joined with event and user metadata via $lookup."""
    history = AnalyticsService.get_user_booking_history(limit=100)
    return jsonify({
        "success": True,
        "count": len(history),
        "bookings": history
    }), 200

@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """List registered users for administration."""
    users = UserService.list_users(limit=100)
    for u in users:
        u.pop("password_hash", None)
    return jsonify({
        "success": True,
        "count": len(users),
        "users": users
    }), 200

@admin_bp.route("/events", methods=["GET"])
@admin_required
def list_all_events():
    """List all events including drafts and cancelled events for management."""
    events = EventService.list_events(status=None, limit=100)
    return jsonify({
        "success": True,
        "count": len(events),
        "events": events
    }), 200

@admin_bp.route("/users/<user_id>/role", methods=["PUT"])
@admin_required
def update_user_role(user_id):
    """
    Promote or update a user's role (Admin only).
    Ensures only an existing authenticated admin can promote another user to admin.
    """
    data = request.get_json() or {}
    new_role = data.get("role")

    if new_role not in ["user", "admin"]:
        return jsonify({
            "success": False,
            "error": "Invalid role. Role must be 'user' or 'admin'."
        }), 400

    try:
        updated_user = UserService.update_user(user_id, {"role": new_role})
        if not updated_user:
            return jsonify({"success": False, "error": "User not found."}), 404

        updated_user.pop("password_hash", None)
        return jsonify({
            "success": True,
            "message": f"User role successfully updated to '{new_role}'.",
            "user": updated_user
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to update role: {str(e)}"}), 500
