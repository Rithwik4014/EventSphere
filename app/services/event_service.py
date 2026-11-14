# app/services/event_service.py
"""
Event Service for EventSphere.
Implements CRUD operations with PyMongo, handling ObjectId conversions,
full-text searches, and schema validation.
"""

from datetime import datetime
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure
from .db import get_db, to_object_id

VALID_CATEGORIES = [
    "Technology & Innovation",
    "Education & Learning",
    "Music & Entertainment",
    "Arts & Creativity",
    "Sports & Fitness",
    "Business & Entrepreneurship",
    "Health & Wellness",
    "Food & Lifestyle",
    "Travel & Adventure",
    "Social & Community",
    "Academic",
    "Technology",
    "Cultural",
    "Sports",
    "Gaming",
    "Wellness",
    "Workshop",
    "Business"
]

CATEGORY_DEFAULT_IMAGES = {
    "Technology & Innovation": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80",
    "Education & Learning": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=800&q=80",
    "Music & Entertainment": "https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=800&q=80",
    "Arts & Creativity": "https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?auto=format&fit=crop&w=800&q=80",
    "Sports & Fitness": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?auto=format&fit=crop&w=800&q=80",
    "Business & Entrepreneurship": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=800&q=80",
    "Health & Wellness": "https://images.unsplash.com/photo-1545205597-3d9d02c29597?auto=format&fit=crop&w=800&q=80",
    "Food & Lifestyle": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80",
    "Travel & Adventure": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
    "Social & Community": "https://images.unsplash.com/photo-1511632765486-a01980e01a18?auto=format&fit=crop&w=800&q=80",
    "Cultural": "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&w=800&q=80",
    "Gaming": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=800&q=80",
    "Workshop": "https://images.unsplash.com/photo-1531482615713-2afd69097998?auto=format&fit=crop&w=800&q=80"
}

class EventService:
    @staticmethod
    def get_collection():
        return get_db().events

    @classmethod
    def create_event(
        cls,
        title,
        description,
        category,
        organizer_id,
        organizer_name,
        venue,
        event_date,
        duration_hours,
        total_capacity,
        price=0.0,
        tags=None,
        status="published",
        image_url=None
    ):
        """
        Create a new event document in MongoDB.
        Enforces schema requirements and initializes remaining_capacity.
        """
        org_oid = to_object_id(organizer_id)
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")

        if not isinstance(venue, dict) or "type" not in venue or "name" not in venue:
            raise ValueError("Venue must be an object with at least 'type' and 'name' fields.")

        if not isinstance(event_date, datetime):
            raise ValueError("event_date must be a valid Python datetime object.")

        total_cap = int(total_capacity)
        if total_cap < 1:
            raise ValueError("total_capacity must be at least 1.")

        now = datetime.utcnow()
        event_doc = {
            "title": title.strip(),
            "description": description.strip(),
            "category": category,
            "tags": tags or [],
            "organizer_id": org_oid,
            "organizer_name": organizer_name.strip(),
            "venue": {
                "type": venue.get("type", "in-person"),
                "name": venue.get("name", "").strip(),
                "address_or_link": venue.get("address_or_link", "").strip(),
                "city": venue.get("city", "").strip()
            },
            "event_date": event_date,
            "duration_hours": float(duration_hours),
            "total_capacity": total_cap,
            "remaining_capacity": total_cap,
            "price": float(price),
            "status": status if status in ["draft", "published", "cancelled", "completed"] else "published",
            "image_url": image_url or CATEGORY_DEFAULT_IMAGES.get(category, "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=800&q=80"),
            "created_at": now,
            "updated_at": now
        }

        try:
            result = cls.get_collection().insert_one(event_doc)
            event_doc["_id"] = result.inserted_id
            return event_doc
        except OperationFailure as e:
            err_msg = e.details.get("errmsg", str(e)) if hasattr(e, "details") else str(e)
            raise ValueError(f"Event document failed schema validation: {err_msg}") from e

    @classmethod
    def get_event_by_id(cls, event_id):
        """Find an event document by its ObjectId or hex string."""
        oid = to_object_id(event_id)
        return cls.get_collection().find_one({"_id": oid})

    @classmethod
    def list_events(
        cls,
        category=None,
        status="published",
        upcoming_only=False,
        sort_by="event_date",
        limit=50,
        skip=0
    ):
        """Query and paginate events with optional category and date filtering."""
        query = {}
        if status:
            query["status"] = status
        if category:
            query["category"] = category
        if upcoming_only:
            query["event_date"] = {"$gte": datetime.utcnow()}

        sort_dir = ASCENDING if sort_by in ["event_date", "price"] else DESCENDING
        cursor = cls.get_collection().find(query).sort(sort_by, sort_dir).skip(skip).limit(limit)
        return list(cursor)

    @classmethod
    def search_events(cls, search_text, category=None, limit=20):
        """Full-text search on title, description, and tags using the text index."""
        if not search_text:
            return cls.list_events(category=category, limit=limit)

        query = {"$text": {"$search": search_text}}
        if category:
            query["category"] = category
        query["status"] = "published"

        cursor = cls.get_collection().find(
            query,
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        return list(cursor)

    @classmethod
    def update_event(cls, event_id, update_fields):
        """Update event fields and automatically bump updated_at timestamp."""
        oid = to_object_id(event_id)
        if not update_fields:
            return cls.get_event_by_id(oid)

        existing = cls.get_event_by_id(oid)
        if not existing:
            return None

        sanitized = {k: v for k, v in update_fields.items() if k not in ["_id", "created_at"]}
        if "organizer_id" in sanitized:
            sanitized["organizer_id"] = to_object_id(sanitized["organizer_id"])

        if "category" in sanitized and sanitized["category"] not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{sanitized['category']}'. Must be one of: {VALID_CATEGORIES}")

        if "price" in sanitized:
            sanitized["price"] = float(sanitized["price"])
            if sanitized["price"] < 0:
                raise ValueError("Price must be a non-negative number.")

        if "duration_hours" in sanitized:
            sanitized["duration_hours"] = float(sanitized["duration_hours"])
            if sanitized["duration_hours"] < 0.5:
                raise ValueError("Duration must be at least 0.5 hours.")

        if "total_capacity" in sanitized:
            new_total = int(sanitized["total_capacity"])
            if new_total < 1:
                raise ValueError("Total capacity must be at least 1.")
            cur_total = existing.get("total_capacity", new_total)
            cur_remaining = existing.get("remaining_capacity", new_total)
            booked_seats = cur_total - cur_remaining
            if new_total < booked_seats:
                raise ValueError(f"Cannot reduce capacity below currently booked seats ({booked_seats}).")
            sanitized["total_capacity"] = new_total
            sanitized["remaining_capacity"] = new_total - booked_seats

        if "event_date" in sanitized:
            ev_date = sanitized["event_date"]
            if isinstance(ev_date, str):
                ev_date = datetime.fromisoformat(ev_date.replace("Z", "+00:00"))
            compare_date = ev_date.replace(tzinfo=None) if ev_date.tzinfo else ev_date
            if compare_date <= datetime.utcnow():
                raise ValueError("New event date and time must be set to a future date.")
            sanitized["event_date"] = compare_date
            sanitized["previous_event_date"] = existing.get("event_date")
            sanitized["rescheduled_at"] = datetime.utcnow()

        sanitized["updated_at"] = datetime.utcnow()

        try:
            result = cls.get_collection().find_one_and_update(
                {"_id": oid},
                {"$set": sanitized},
                return_document=True
            )
            return result
        except OperationFailure as e:
            err_msg = e.details.get("errmsg", str(e)) if hasattr(e, "details") else str(e)
            raise ValueError(f"Event update failed schema validation: {err_msg}") from e

    @classmethod
    def reschedule_event(cls, event_id, new_event_date, admin_id=None, reason=None):
        """
        Reschedule an existing event to a future date.
        1. Validates that the event exists and the new date is strictly in the future.
        2. Atomically updates the existing event document without creating duplicates.
        3. Preserves all bookings, booking codes, ticket records, and seat capacities.
        4. Records previous_event_date, rescheduled_at, and appends to reschedule_history for audit.
        """
        oid = to_object_id(event_id)
        event = cls.get_event_by_id(oid)
        if not event:
            raise ValueError("Event not found.")

        if isinstance(new_event_date, str):
            try:
                new_event_date = datetime.fromisoformat(new_event_date.replace("Z", "+00:00"))
            except Exception as e:
                raise ValueError(f"Invalid new_event_date format: {str(e)}")

        if not isinstance(new_event_date, datetime):
            raise ValueError("new_event_date must be a valid datetime object or ISO string.")

        now = datetime.utcnow()
        compare_date = new_event_date.replace(tzinfo=None) if new_event_date.tzinfo else new_event_date
        if compare_date <= now:
            raise ValueError("New event date and time must be set to a future date.")

        previous_event_date = event.get("event_date")

        audit_entry = {
            "previous_event_date": previous_event_date,
            "new_event_date": compare_date,
            "rescheduled_at": now,
            "rescheduled_by": str(admin_id) if admin_id else "admin",
            "reason": (reason or "").strip() or "Administrative schedule change"
        }

        try:
            result = cls.get_collection().find_one_and_update(
                {"_id": oid},
                {
                    "$set": {
                        "event_date": compare_date,
                        "previous_event_date": previous_event_date,
                        "rescheduled_at": now,
                        "updated_at": now
                    },
                    "$push": {
                        "reschedule_history": audit_entry
                    }
                },
                return_document=True
            )
            return result
        except OperationFailure as e:
            err_msg = e.details.get("errmsg", str(e)) if hasattr(e, "details") else str(e)
            raise ValueError(f"Event reschedule failed schema validation: {err_msg}") from e

    @classmethod
    def cancel_event(cls, event_id):
        """Soft-delete an event by marking its status as 'cancelled'."""
        return cls.update_event(event_id, {"status": "cancelled"})

    @classmethod
    def delete_event(cls, event_id):
        """Hard delete an event document from the database."""
        oid = to_object_id(event_id)
        result = cls.get_collection().delete_one({"_id": oid})
        return result.deleted_count > 0
