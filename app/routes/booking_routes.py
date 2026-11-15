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

@bookings_bp.route("/verify", methods=["GET", "POST"])
@admin_required
def verify_ticket():
    """
    Gate verification endpoint.
    Restricted to authenticated administrators and gate staff (@admin_required).
    Accepts:
    - POST JSON: {"payload": "booking_code|user_id|event_id", "check_in": false}
    - GET query: /api/bookings/verify?payload=...&check_in=false
    Strictly verifies existence, matching code, matching user and event IDs,
    and confirmed status. Rejects cancelled or tampered tickets.
    Prevents duplicate check-ins.
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        payload = data.get("payload") or request.form.get("payload")
        check_in = data.get("check_in", False)
    else:
        payload = request.args.get("payload")
        check_in = request.args.get("check_in", "false").lower() in ["true", "1", "yes"]

    if not payload:
        return jsonify({
            "success": False,
            "verified": False,
            "error": "Verification payload is required. Expected format: 'booking_code|user_id|event_id'."
        }), 400

    result = BookingService.verify_ticket_payload(payload, check_in=check_in)
    
    if result.get("verified"):
        status_code = 200
    elif result.get("already_checked_in"):
        status_code = 409
    else:
        status_code = 400

    return jsonify({
        "success": result.get("verified", False),
        **result
    }), status_code

@bookings_bp.route("/check-in", methods=["POST"])
@admin_required
def check_in_ticket():
    """
    Secure gate check-in endpoint.
    Restricted to authenticated administrators (@admin_required).
    Accepts:
    - POST JSON: {"payload": "booking_code|user_id|event_id"}
      OR {"booking_code": "...", "user_id": "...", "event_id": "..."}
      OR {"booking_id": "..."}
    Validates booking code, user ID, event ID, and confirmed status.
    Updates booking with:
    - checked_in: true
    - checked_in_at: current UTC timestamp
    - status: 'checked_in'
    Prevents duplicate check-ins (returns 409 Conflict).
    Returns attendee and event details for green confirmation receipt.
    """
    data = request.get_json(silent=True) or {}
    payload = data.get("payload") or request.form.get("payload")
    booking_code = data.get("booking_code")
    user_id = data.get("user_id")
    event_id = data.get("event_id")
    booking_id = data.get("booking_id")

    if not payload and not booking_code and not booking_id:
        return jsonify({
            "success": False,
            "checked_in": False,
            "error": "Booking verification payload or booking code required for check-in."
        }), 400

    result = BookingService.check_in_ticket(
        payload=payload,
        booking_code=booking_code,
        user_id=user_id,
        event_id=event_id,
        booking_id=booking_id
    )

    if result.get("checked_in"):
        status_code = 200
    elif result.get("already_checked_in"):
        status_code = 409
    elif "not found" in result.get("error", "").lower():
        status_code = 404
    else:
        status_code = 400

    return jsonify(result), status_code

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

        # Attach genuine dynamically generated QR code data URI and direct image URL
        payload = booking.get("ticket_details", {}).get("qr_payload")
        if not payload:
            payload = f"{booking.get('booking_code')}|{str(booking.get('user_id'))}|{str(booking.get('event_id'))}"
        booking["qr_code_data_url"] = BookingService.generate_qr_code_base64(payload)
        booking["qr_image_url"] = f"/api/bookings/{booking_id}/qr"

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
    data = request.get_json(silent=True) or {}
    payload = data.get("payload")
    user_id = data.get("user_id")
    event_id = data.get("event_id")

    result = BookingService.check_in_ticket(
        payload=payload,
        user_id=user_id,
        event_id=event_id,
        booking_id=booking_id
    )

    if result.get("checked_in"):
        return jsonify({
            "success": True,
            "message": "Ticket checked in successfully.",
            **result
        }), 200
    elif result.get("already_checked_in"):
        return jsonify(result), 409
    elif "not found" in result.get("error", "").lower():
        return jsonify(result), 404
    else:
        return jsonify(result), 400

@bookings_bp.route("/<booking_id>/qr", methods=["GET"])
@login_required
def get_booking_qr_image(booking_id):
    """
    Generate and return the genuine QR code PNG image for a booking.
    Restricted to booking owner or administrator.
    """
    user_id = get_current_user_id()
    role = get_current_user_role()

    try:
        booking = BookingService.get_booking_by_id(booking_id)
        if not booking:
            return jsonify({"success": False, "error": "Booking not found."}), 404

        if str(booking.get("user_id")) != str(user_id) and role != "admin":
            return jsonify({"success": False, "error": "Unauthorized access to ticket QR."}), 403

        png_bytes = BookingService.get_booking_qr_bytes(booking_id)
        from flask import Response
        return Response(png_bytes, mimetype="image/png")
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
