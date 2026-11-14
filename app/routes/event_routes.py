# app/routes/event_routes.py
"""
Events Blueprint for EventSphere.
Handles event discovery, searching, single-event lookups, and admin CRUD routes.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from app.services.event_service import EventService
from .auth_helpers import admin_required, get_current_user_id

events_bp = Blueprint("events_bp", __name__, url_prefix="/api/events")

@events_bp.route("", methods=["GET"])
def list_events():
    """List events with optional category, status, and upcoming filters."""
    category = request.args.get("category")
    status = request.args.get("status", "published")
    upcoming = request.args.get("upcoming", "false").lower() == "true"
    sort_by = request.args.get("sort_by", "event_date")
    limit = int(request.args.get("limit", 50))
    skip = int(request.args.get("skip", 0))

    events = EventService.list_events(
        category=category,
        status=status,
        upcoming_only=upcoming,
        sort_by=sort_by,
        limit=limit,
        skip=skip
    )

    return jsonify({
        "success": True,
        "count": len(events),
        "events": events
    }), 200

@events_bp.route("/search", methods=["GET"])
def search_events():
    """Full-text search on title, description, and tags."""
    query = request.args.get("q", "").strip()
    category = request.args.get("category")
    limit = int(request.args.get("limit", 20))

    if not query:
        return jsonify({
            "success": False,
            "error": "Query parameter 'q' is required for search."
        }), 400

    results = EventService.search_events(search_text=query, category=category, limit=limit)

    return jsonify({
        "success": True,
        "query": query,
        "count": len(results),
        "events": results
    }), 200

@events_bp.route("/<event_id>", methods=["GET"])
def get_event(event_id):
    """Retrieve details of a single event."""
    try:
        event = EventService.get_event_by_id(event_id)
        if not event:
            return jsonify({"success": False, "error": "Event not found."}), 404
        return jsonify({"success": True, "event": event}), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@events_bp.route("", methods=["POST"])
@admin_required
def create_event():
    """Create a new event document (Admin only)."""
    data = request.get_json() or {}

    required = ["title", "description", "category", "venue", "event_date", "total_capacity"]
    for field in required:
        if field not in data:
            return jsonify({
                "success": False,
                "error": f"Missing required field: '{field}'."
            }), 400

    # Parse ISO 8601 date string
    try:
        event_date_val = data["event_date"]
        if isinstance(event_date_val, str):
            event_date = datetime.fromisoformat(event_date_val.replace("Z", "+00:00"))
        else:
            event_date = event_date_val
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Invalid event_date format. Expected ISO-8601 string: {str(e)}"
        }), 400

    organizer_id = get_current_user_id()
    organizer_name = data.get("organizer_name", "EventSphere Organizer")

    try:
        event = EventService.create_event(
            title=data["title"],
            description=data["description"],
            category=data["category"],
            organizer_id=organizer_id,
            organizer_name=organizer_name,
            venue=data["venue"],
            event_date=event_date,
            duration_hours=float(data.get("duration_hours", 2.0)),
            total_capacity=int(data["total_capacity"]),
            price=float(data.get("price", 0.0)),
            tags=data.get("tags", []),
            status=data.get("status", "published"),
            image_url=data.get("image_url", "")
        )
        return jsonify({
            "success": True,
            "message": "Event created successfully.",
            "event": event
        }), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to create event: {str(e)}"}), 500

@events_bp.route("/<event_id>", methods=["PUT"])
@admin_required
def update_event(event_id):
    """Update an existing event (Admin only)."""
    data = request.get_json() or {}

    # Convert event_date string if present
    if "event_date" in data and isinstance(data["event_date"], str):
        try:
            data["event_date"] = datetime.fromisoformat(data["event_date"].replace("Z", "+00:00"))
        except Exception as e:
            return jsonify({"success": False, "error": f"Invalid event_date: {str(e)}"}), 400

    try:
        updated = EventService.update_event(event_id, data)
        if not updated:
            return jsonify({"success": False, "error": "Event not found."}), 404
        return jsonify({
            "success": True,
            "message": "Event updated successfully.",
            "event": updated
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@events_bp.route("/<event_id>/reschedule", methods=["POST", "PUT"])
@admin_required
def reschedule_event(event_id):
    """
    Reschedule an existing event to a future date (Admin only).
    Validates future date, updates document, records audit trail,
    and preserves all bookings and capacities.
    """
    data = request.get_json() or {}
    new_date_str = data.get("new_event_date") or data.get("event_date")
    reason = data.get("reason", "")

    if not new_date_str:
        return jsonify({
            "success": False,
            "error": "New event date and time is required."
        }), 400

    try:
        new_event_date = datetime.fromisoformat(new_date_str.replace("Z", "+00:00"))
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Invalid date format. Expected ISO-8601 string: {str(e)}"
        }), 400

    admin_id = get_current_user_id()
    try:
        rescheduled = EventService.reschedule_event(
            event_id=event_id,
            new_event_date=new_event_date,
            admin_id=admin_id,
            reason=reason
        )
        if not rescheduled:
            return jsonify({"success": False, "error": "Event not found."}), 404

        return jsonify({
            "success": True,
            "message": "Event rescheduled successfully.",
            "event": rescheduled
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to reschedule event: {str(e)}"}), 500

@events_bp.route("/<event_id>/cancel", methods=["POST"])
@admin_required
def cancel_event(event_id):
    """Soft-cancel an event (Admin only)."""
    try:
        cancelled = EventService.cancel_event(event_id)
        if not cancelled:
            return jsonify({"success": False, "error": "Event not found."}), 404
        return jsonify({
            "success": True,
            "message": "Event cancelled successfully.",
            "event": cancelled
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@events_bp.route("/<event_id>", methods=["DELETE"])
@admin_required
def delete_event(event_id):
    """Hard-delete an event (Admin only)."""
    try:
        deleted = EventService.delete_event(event_id)
        if not deleted:
            return jsonify({"success": False, "error": "Event not found."}), 404
        return jsonify({
            "success": True,
            "message": "Event deleted successfully."
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
