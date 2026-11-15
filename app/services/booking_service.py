# app/services/booking_service.py
"""
Booking Service for EventSphere.
Implements CRUD operations with PyMongo, including multi-document ACID transactions
for atomic seat reservations and cancellations.
"""

import io
import base64
import uuid
import qrcode
from datetime import datetime
from pymongo import ReturnDocument, DESCENDING
from pymongo.errors import OperationFailure, PyMongoError
from .db import get_client, get_db, to_object_id

class BookingService:
    @staticmethod
    def get_collection():
        return get_db().bookings

    @classmethod
    def create_booking(
        cls,
        user_id,
        event_id,
        tickets_count,
        attendee_name,
        attendee_email
    ):
        """
        Execute an atomic booking transaction:
        1. Verifies event exists, is published, and has enough seats.
        2. Atomically decrements remaining_capacity in 'events'.
        3. Inserts a new confirmed booking in 'bookings'.
        All executed within a PyMongo ClientSession transaction.
        """
        user_oid = to_object_id(user_id)
        event_oid = to_object_id(event_id)
        count = int(tickets_count)

        if count < 1 or count > 5:
            raise ValueError("You can book between 1 and 5 tickets per transaction.")
        if not attendee_name or not attendee_email:
            raise ValueError("Attendee name and email are required for ticket generation.")

        client = get_client()
        db = get_db()

        with client.start_session() as session:
            with session.start_transaction():
                # Step 1: Atomic capacity check & decrement inside transaction
                event = db.events.find_one_and_update(
                    {
                        "_id": event_oid,
                        "status": "published",
                        "remaining_capacity": {"$gte": count}
                    },
                    {"$inc": {"remaining_capacity": -count}},
                    session=session,
                    return_document=ReturnDocument.AFTER
                )

                if not event:
                    raise ValueError(
                        f"Cannot complete booking: Insufficient capacity or event is not active."
                    )

                # Step 2: Calculate total amount and generate unique booking code
                unit_price = float(event.get("price", 0.0))
                total_amount = float(count * unit_price)
                booking_code = f"EVT-2026-{uuid.uuid4().hex[:6].upper()}"
                now = datetime.utcnow()

                qr_payload = f"{booking_code}|{str(user_oid)}|{str(event_oid)}"

                booking_doc = {
                    "booking_code": booking_code,
                    "user_id": user_oid,
                    "event_id": event_oid,
                    "booking_date": now,
                    "tickets_count": count,
                    "total_amount": total_amount,
                    "status": "confirmed",
                    "ticket_details": {
                        "attendee_name": attendee_name.strip(),
                        "attendee_email": attendee_email.strip().lower(),
                        "qr_payload": qr_payload,
                        "checked_in_at": None
                    },
                    "cancelled_at": None
                }

                # Step 3: Insert booking document inside transaction
                try:
                    result = db.bookings.insert_one(booking_doc, session=session)
                    booking_doc["_id"] = result.inserted_id
                    return booking_doc
                except OperationFailure as e:
                    err_msg = e.details.get("errmsg", str(e)) if hasattr(e, "details") else str(e)
                    raise ValueError(f"Booking document failed schema validation: {err_msg}") from e

    @classmethod
    def cancel_booking(cls, booking_id, user_id=None):
        """
        Execute an atomic cancellation transaction:
        1. Locates the confirmed booking.
        2. Sets status to 'cancelled' and records cancelled_at.
        3. Restores tickets_count back to remaining_capacity in 'events'.
        """
        b_oid = to_object_id(booking_id)
        query = {"_id": b_oid, "status": "confirmed"}
        if user_id:
            query["user_id"] = to_object_id(user_id)

        client = get_client()
        db = get_db()

        with client.start_session() as session:
            with session.start_transaction():
                # Step 1: Update booking status
                booking = db.bookings.find_one_and_update(
                    query,
                    {
                        "$set": {
                            "status": "cancelled",
                            "cancelled_at": datetime.utcnow()
                        }
                    },
                    session=session,
                    return_document=ReturnDocument.BEFORE
                )

                if not booking:
                    raise ValueError("Booking not found or is already cancelled.")

                # Step 2: Restock capacity
                tickets_to_restore = booking.get("tickets_count", 1)
                db.events.update_one(
                    {"_id": booking["event_id"]},
                    {"$inc": {"remaining_capacity": tickets_to_restore}},
                    session=session
                )

                return True

    @classmethod
    def get_booking_by_id(cls, booking_id):
        """Retrieve a booking by its ObjectId or hex string."""
        oid = to_object_id(booking_id)
        return cls.get_collection().find_one({"_id": oid})

    @classmethod
    def get_booking_by_code(cls, booking_code):
        """Retrieve a booking by its unique alphanumeric reference code."""
        if not booking_code:
            return None
        return cls.get_collection().find_one({"booking_code": booking_code.strip()})

    @classmethod
    def get_user_bookings(cls, user_id, status=None):
        """Retrieve all bookings for a user, sorted newest first, enriched with current event data."""
        user_oid = to_object_id(user_id)
        query = {"user_id": user_oid}
        if status:
            query["status"] = status
        bookings = list(cls.get_collection().find(query).sort("booking_date", DESCENDING))

        if bookings:
            event_ids = list({b["event_id"] for b in bookings if "event_id" in b})
            events_map = {e["_id"]: e for e in get_db().events.find({"_id": {"$in": event_ids}})}
            for b in bookings:
                ev = events_map.get(b.get("event_id"))
                if ev:
                    b["event_title"] = ev.get("title")
                    b["event_date"] = ev.get("event_date")
                    b["event_category"] = ev.get("category")
                    b["event_venue"] = ev.get("venue", {}).get("name")
                    b["is_rescheduled"] = bool(ev.get("rescheduled_at"))
                    b["previous_event_date"] = ev.get("previous_event_date")
        return bookings

    @classmethod
    def get_event_bookings(cls, event_id, status=None):
        """Retrieve all bookings for an event."""
        event_oid = to_object_id(event_id)
        query = {"event_id": event_oid}
        if status:
            query["status"] = status
        return list(cls.get_collection().find(query).sort("booking_date", DESCENDING))

    @classmethod
    def check_in_booking(cls, booking_id):
        """Mark a booking ticket as checked-in."""
        oid = to_object_id(booking_id)
        now = datetime.utcnow()
        result = cls.get_collection().find_one_and_update(
            {"_id": oid, "status": "confirmed"},
            {
                "$set": {
                    "status": "checked_in",
                    "checked_in": True,
                    "checked_in_at": now,
                    "ticket_details.checked_in_at": now,
                    "updated_at": now
                }
            },
            return_document=ReturnDocument.AFTER
        )
        if not result:
            raise ValueError("Booking cannot be checked in (either invalid or not confirmed).")
        return result

    @classmethod
    def delete_booking(cls, booking_id):
        """Delete a booking document by ID."""
        oid = to_object_id(booking_id)
        result = cls.get_collection().delete_one({"_id": oid})
        return result.deleted_count > 0

    # -------------------------------------------------------------
    # Genuine QR Code Generation & Ticket Verification
    # -------------------------------------------------------------

    @classmethod
    def generate_qr_code_bytes(cls, payload: str, box_size: int = 8, border: int = 2) -> bytes:
        """
        Generate a genuine QR code PNG using qrcode and Pillow, returned as raw bytes.
        """
        if not payload or not isinstance(payload, str):
            raise ValueError("QR payload must be a non-empty string.")

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(payload.strip())
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @classmethod
    def generate_qr_code_base64(cls, payload: str, box_size: int = 8, border: int = 2) -> str:
        """
        Generate a genuine QR code PNG using qrcode and Pillow, returned as a Base64 Data URI.
        """
        raw_bytes = cls.generate_qr_code_bytes(payload, box_size=box_size, border=border)
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    @classmethod
    def get_booking_qr_bytes(cls, booking_id: str) -> bytes:
        """
        Retrieve QR code PNG bytes for a given booking document ID.
        """
        booking = cls.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError("Booking not found.")

        payload = booking.get("ticket_details", {}).get("qr_payload")
        if not payload:
            payload = f"{booking.get('booking_code')}|{str(booking.get('user_id'))}|{str(booking.get('event_id'))}"

        return cls.generate_qr_code_bytes(payload)

    @classmethod
    def verify_ticket_payload(cls, payload: str, check_in: bool = False) -> dict:
        """
        Verify a scanned QR payload against MongoDB records.
        Strict verification rules:
        1. Validates payload format: 'booking_code|user_id|event_id'.
        2. Validates hexadecimal 24-character ObjectId formats.
        3. Looks up booking in MongoDB Atlas (never relies solely on payload).
        4. Verifies booking_code, user_id, and event_id exact match.
        5. Verifies booking status:
           - Cancelled tickets ('status': 'cancelled') are strictly rejected.
           - Already checked-in tickets ('status': 'checked_in') are detected to prevent duplicate check-in.
        6. When check_in=True and status is confirmed:
           - Atomically updates status to 'checked_in', checked_in to true, and checked_in_at timestamp.
           - Preserves all original booking records (tickets_count, total_amount, booking_date, etc.).
        7. Data Privacy: Sanitizes output to return only necessary attendee/event gate information.
           Never exposes passwords, hashes, reset tokens, or private user preferences.
        """
        if not payload or not isinstance(payload, str):
            return {
                "verified": False,
                "error": "Missing or empty QR verification payload."
            }

        parts = payload.strip().split("|")
        if len(parts) != 3:
            return {
                "verified": False,
                "error": "Invalid QR payload format. Expected 'booking_code|user_id|event_id'."
            }

        booking_code, user_id_str, event_id_str = parts[0].strip(), parts[1].strip(), parts[2].strip()

        if not booking_code:
            return {"verified": False, "error": "Booking code in payload is empty."}

        try:
            user_oid = to_object_id(user_id_str)
            event_oid = to_object_id(event_id_str)
        except ValueError:
            return {
                "verified": False,
                "error": "Invalid user or event identifier format in payload."
            }

        # Query MongoDB - NEVER verify without checking the database record
        booking = cls.get_collection().find_one({"booking_code": booking_code})
        if not booking:
            return {
                "verified": False,
                "error": f"No booking found for code '{booking_code}' in database."
            }

        # Check user_id and event_id exact match
        if booking.get("user_id") != user_oid:
            return {
                "verified": False,
                "error": "User identifier mismatch: ticket does not belong to the recorded attendee."
            }

        if booking.get("event_id") != event_oid:
            return {
                "verified": False,
                "error": "Event identifier mismatch: ticket does not match the recorded event."
            }

        status = booking.get("status")
        ticket_details = booking.get("ticket_details", {})

        # Strict rejection of cancelled bookings
        if status == "cancelled":
            cancelled_at = booking.get("cancelled_at")
            return {
                "verified": False,
                "status": "cancelled",
                "cancelled_at": cancelled_at.isoformat() if hasattr(cancelled_at, "isoformat") else str(cancelled_at),
                "error": "This booking has been cancelled and is no longer valid."
            }

        # Duplicate check-in detection: ticket already scanned/admitted
        is_already_checked_in = (
            status == "checked_in" or
            booking.get("checked_in") is True or
            ticket_details.get("checked_in_at") is not None
        )
        if is_already_checked_in:
            checked_in_at = booking.get("checked_in_at") or ticket_details.get("checked_in_at")
            checked_in_at_str = checked_in_at.isoformat() if hasattr(checked_in_at, "isoformat") else str(checked_in_at)
            return {
                "verified": False,
                "already_checked_in": True,
                "status": "checked_in",
                "booking_code": booking_code,
                "attendee_name": ticket_details.get("attendee_name", "Attendee"),
                "checked_in_at": checked_in_at_str,
                "error": f"DUPLICATE SCAN: Ticket has already been checked in at {checked_in_at_str}. Duplicate admission prevented."
            }

        if status != "confirmed":
            return {
                "verified": False,
                "status": status,
                "error": f"Ticket cannot be verified because status is '{status}'."
            }

        # Perform atomic check-in if requested
        now = datetime.utcnow()
        if check_in:
            updated_booking = cls.get_collection().find_one_and_update(
                {"_id": booking["_id"], "status": "confirmed"},
                {
                    "$set": {
                        "status": "checked_in",
                        "checked_in": True,
                        "checked_in_at": now,
                        "ticket_details.checked_in_at": now,
                        "updated_at": now
                    }
                },
                return_document=ReturnDocument.AFTER
            )
            if not updated_booking:
                # Concurrent scan race condition handled atomically
                return {
                    "verified": False,
                    "already_checked_in": True,
                    "status": "checked_in",
                    "error": "Ticket was just checked in concurrently. Duplicate admission prevented."
                }
            booking = updated_booking
            status = "checked_in"
            checked_in_time = now
        else:
            checked_in_time = None

        # Fetch event title and venue for verification receipt (without exposing sensitive info)
        event = get_db().events.find_one({"_id": event_oid})
        event_title = event.get("title", "Event") if event else "Unknown Event"
        event_venue = event.get("venue", {}).get("name", "Venue TBD") if event else "TBD"
        event_date = event.get("event_date") if event else None

        return {
            "verified": True,
            "status": status,
            "already_checked_in": False,
            "booking_id": str(booking["_id"]),
            "booking_code": booking_code,
            "user_id": str(user_oid),
            "event_id": str(event_oid),
            "attendee_name": ticket_details.get("attendee_name", "Attendee"),
            "attendee_email": ticket_details.get("attendee_email", ""),
            "tickets_count": booking.get("tickets_count", 1),
            "event_title": event_title,
            "event_venue": event_venue,
            "event_date": event_date.isoformat() if hasattr(event_date, "isoformat") else str(event_date),
            "checked_in": check_in,
            "checked_in_at": checked_in_time.isoformat() if checked_in_time else None,
            "message": "Ticket verified successfully. Ready for check-in." if not check_in else "Ticket verified and checked in successfully."
        }

    @classmethod
    def check_in_ticket(
        cls,
        payload: str = None,
        booking_code: str = None,
        user_id: str = None,
        event_id: str = None,
        booking_id: str = None
    ) -> dict:
        """
        Securely check in a verified ticket booking.
        Validates:
        1. Booking code, user ID, event ID, and booking status.
        2. Booking exists in MongoDB.
        3. User ID and Event ID match the booking.
        4. Booking status is strictly 'confirmed'.
        5. Rejects cancelled or tampered tickets.
        6. Prevents duplicate check-ins.
        Updates booking document with:
        - checked_in: true
        - checked_in_at: current UTC timestamp
        - status: 'checked_in'
        - ticket_details.checked_in_at: current UTC timestamp
        Returns attendee and event details for green confirmation receipt.
        """
        # Parse payload if provided
        if payload and isinstance(payload, str):
            parts = payload.strip().split("|")
            if len(parts) != 3:
                return {
                    "success": False,
                    "checked_in": False,
                    "error": "Invalid QR payload format. Expected 'booking_code|user_id|event_id'."
                }
            p_code, p_user_id, p_event_id = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if not booking_code:
                booking_code = p_code
            elif booking_code != p_code:
                return {
                    "success": False,
                    "checked_in": False,
                    "error": "Mismatched booking code in payload and request."
                }
            if not user_id:
                user_id = p_user_id
            if not event_id:
                event_id = p_event_id

        # If booking_id is provided but booking_code is not
        if not booking_code and booking_id:
            try:
                b_doc = cls.get_collection().find_one({"_id": to_object_id(booking_id)})
                if b_doc:
                    booking_code = b_doc.get("booking_code")
                    if not user_id:
                        user_id = str(b_doc.get("user_id"))
                    if not event_id:
                        event_id = str(b_doc.get("event_id"))
            except ValueError:
                return {"success": False, "checked_in": False, "error": "Invalid booking_id format."}

        if not booking_code:
            return {"success": False, "checked_in": False, "error": "Booking code is required for check-in."}
        if not user_id:
            return {"success": False, "checked_in": False, "error": "User ID is required for check-in validation."}
        if not event_id:
            return {"success": False, "checked_in": False, "error": "Event ID is required for check-in validation."}

        try:
            user_oid = to_object_id(user_id)
            event_oid = to_object_id(event_id)
        except ValueError:
            return {
                "success": False,
                "checked_in": False,
                "error": "Invalid user or event identifier format."
            }

        # 1. Validate booking existence in MongoDB
        booking = cls.get_collection().find_one({"booking_code": booking_code})
        if not booking:
            return {
                "success": False,
                "checked_in": False,
                "error": f"No booking found for code '{booking_code}' in database."
            }

        # 2. Validate user ID match
        if booking.get("user_id") != user_oid:
            return {
                "success": False,
                "checked_in": False,
                "error": "User identifier mismatch: ticket does not belong to the recorded attendee."
            }

        # 3. Validate event ID match
        if booking.get("event_id") != event_oid:
            return {
                "success": False,
                "checked_in": False,
                "error": "Event identifier mismatch: ticket does not match the recorded event."
            }

        status = booking.get("status")
        ticket_details = booking.get("ticket_details", {})

        # 4. Validate booking status - reject cancelled
        if status == "cancelled":
            return {
                "success": False,
                "checked_in": False,
                "status": "cancelled",
                "error": "This booking has been cancelled and cannot be checked in."
            }

        # 5. Prevent duplicate check-in
        is_already_checked_in = (
            status == "checked_in" or
            booking.get("checked_in") is True or
            ticket_details.get("checked_in_at") is not None
        )
        if is_already_checked_in:
            checked_in_at = booking.get("checked_in_at") or ticket_details.get("checked_in_at")
            checked_in_at_str = checked_in_at.isoformat() if hasattr(checked_in_at, "isoformat") else str(checked_in_at)
            return {
                "success": False,
                "checked_in": False,
                "already_checked_in": True,
                "status": "checked_in",
                "booking_code": booking_code,
                "attendee_name": ticket_details.get("attendee_name", "Attendee"),
                "checked_in_at": checked_in_at_str,
                "message": f"Ticket has already been checked in at {checked_in_at_str}. Duplicate check-in prevented.",
                "error": f"DUPLICATE SCAN: Ticket has already been checked in at {checked_in_at_str}. Duplicate check-in prevented."
            }

        # 6. Only confirmed bookings can be checked in
        if status != "confirmed":
            return {
                "success": False,
                "checked_in": False,
                "status": status,
                "error": f"Only confirmed bookings can be checked in (current status: '{status}')."
            }

        # 7. Atomically perform check-in
        now = datetime.utcnow()
        updated_booking = cls.get_collection().find_one_and_update(
            {"_id": booking["_id"], "status": "confirmed"},
            {
                "$set": {
                    "status": "checked_in",
                    "checked_in": True,
                    "checked_in_at": now,
                    "ticket_details.checked_in_at": now,
                    "updated_at": now
                }
            },
            return_document=ReturnDocument.AFTER
        )
        if not updated_booking:
            # Race condition: checked in concurrently
            return {
                "success": False,
                "checked_in": False,
                "already_checked_in": True,
                "status": "checked_in",
                "message": "Ticket was just checked in concurrently. Duplicate check-in prevented.",
                "error": "Ticket was just checked in concurrently. Duplicate check-in prevented."
            }

        # Fetch event info for green confirmation message
        event = get_db().events.find_one({"_id": event_oid})
        event_title = event.get("title", "Event") if event else "Unknown Event"
        event_venue = event.get("venue", {}).get("name", "Venue TBD") if event else "TBD"
        event_date = event.get("event_date") if event else None

        return {
            "success": True,
            "checked_in": True,
            "already_checked_in": False,
            "status": "checked_in",
            "booking_id": str(updated_booking["_id"]),
            "booking_code": booking_code,
            "user_id": str(user_oid),
            "event_id": str(event_oid),
            "attendee_name": ticket_details.get("attendee_name", "Attendee"),
            "attendee_email": ticket_details.get("attendee_email", ""),
            "tickets_count": updated_booking.get("tickets_count", 1),
            "total_amount": updated_booking.get("total_amount", 0.0),
            "event_title": event_title,
            "event_venue": event_venue,
            "event_date": event_date.isoformat() if hasattr(event_date, "isoformat") else str(event_date),
            "checked_in_at": now.isoformat(),
            "message": f"Ticket {booking_code} checked in successfully."
        }
