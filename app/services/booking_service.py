# app/services/booking_service.py
"""
Booking Service for EventSphere.
Implements CRUD operations with PyMongo, including multi-document ACID transactions
for atomic seat reservations and cancellations.
"""

import uuid
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
        result = cls.get_collection().find_one_and_update(
            {"_id": oid, "status": "confirmed"},
            {
                "$set": {
                    "status": "checked_in",
                    "ticket_details.checked_in_at": datetime.utcnow()
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
