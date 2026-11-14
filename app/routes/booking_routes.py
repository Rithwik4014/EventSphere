# app/routes/booking_routes.py
"""
Bookings Blueprint for EventSphere.
Handles ticket reservations, viewing user tickets, and cancellations
using multi-document ACID transactions via PyMongo.
"""

from flask import Blueprint, request, jsonify
from app.services.booking_service import BookingService
from .auth_helpers import login_required, admin_required, get_current_user_id, get_current_user_role

bookings_bp = Blueprint("bookings_bp", __name__, url_prefix="/api/bookings")

@bookings_bp.route("", methods=["POST"])
@login_required
def create_booking():
    """
    Create a new booking.
    Executes in a PyMongo multi-document ACID transaction:
    checks capacity, decrements seats, and writes booking.
    """
    user_id = get_current_user_id()
    data = request.get_json() or {}

    event_id = data.get("event_id")
    tickets_count = data.get("tickets_count", 1)
    attendee_name = data.get("attendee_name")
    attendee_email = data.get("attendee_email")

    if not event_id:
        return jsonify({"success": False, "error": "event_id is required."}), 400
    if not attendee_name or not attendee_email:
        return jsonify({
            "success": False,
            "error": "attendee_name and attendee_email are required."
        }), 400

    try:
        booking = BookingService.create_booking(
            user_id=user_id,
            event_id=event_id,
            tickets_count=tickets_count,
            attendee_name=attendee_name,
            attendee_email=attendee_email
        )
        return jsonify({
            "success": True,
            "message": "Booking confirmed successfully.",
            "booking": booking
        }), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Booking failed: {str(e)}"}), 500

@bookings_bp.route("/my-tickets", methods=["GET"])
@login_required
def get_my_tickets():
    """Retrieve all bookings placed by the authenticated user."""
    user_id = get_current_user_id()
    status = request.args.get("status")

    try:
        bookings = BookingService.get_user_bookings(user_id=user_id, status=status)
        return jsonify({
            "success": True,
            "count": len(bookings),
            "bookings": bookings
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@bookings_bp.route("/<booking_id>", methods=["GET"])
@login_required
def get_booking(booking_id):
    """Retrieve a single booking document by its ID."""
    user_id = get_current_user_id()
    role = get_current_user_role()

    try:
        booking = BookingService.get_booking_by_id(booking_id)
        if not booking:
            return jsonify({"success": False, "error": "Booking not found."}), 404

        # Verify ownership unless admin
        if str(booking.get("user_id")) != str(user_id) and role != "admin":
            return jsonify({"success": False, "error": "Unauthorized access to ticket."}), 403

        return jsonify({"success": True, "booking": booking}), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@bookings_bp.route("/code/<booking_code>", methods=["GET"])
def get_booking_by_code(booking_code):
    """Retrieve booking by its public booking reference code (for QR ticket verification)."""
    booking = BookingService.get_booking_by_code(booking_code)
    if not booking:
        return jsonify({"success": False, "error": "Invalid ticket code."}), 404
    return jsonify({"success": True, "booking": booking}), 200

@bookings_bp.route("/<booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    """
    Cancel a booking reservation.
    Executes an atomic transaction updating status to 'cancelled' and restocking seats.
    """
    user_id = get_current_user_id()
    role = get_current_user_role()

    # Pass user_id to enforce ownership unless admin
    enforce_user_id = None if role == "admin" else user_id

    try:
        BookingService.cancel_booking(booking_id=booking_id, user_id=enforce_user_id)
        return jsonify({
            "success": True,
            "message": "Booking cancelled and seats restocked successfully."
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Cancellation failed: {str(e)}"}), 500

@bookings_bp.route("/<booking_id>/check-in", methods=["POST"])
@admin_required
def check_in_booking(booking_id):
    """Mark ticket as checked in upon venue arrival (Admin/Organizer only)."""
    try:
        updated = BookingService.check_in_booking(booking_id)
        return jsonify({
            "success": True,
            "message": "Ticket checked in successfully.",
            "booking": updated
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
