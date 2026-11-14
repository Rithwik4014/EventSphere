# app/models/schemas.py
"""
MongoDB $jsonSchema definitions for EventSphere collections:
- users
- events
- bookings
"""

USER_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "email", "password_hash", "role", "created_at"],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "name": {
                "bsonType": "string",
                "description": "Full name of the user (required, 2-100 characters)"
            },
            "email": {
                "bsonType": "string",
                "pattern": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$",
                "description": "Valid unique email address"
            },
            "password_hash": {
                "bsonType": "string",
                "description": "Bcrypt or Werkzeug hashed password string"
            },
            "role": {
                "enum": ["user", "admin"],
                "description": "Access role: user or admin"
            },
            "preferences": {
                "bsonType": "object",
                "description": "Embedded user preference document",
                "properties": {
                    "favorite_categories": {
                        "bsonType": "array",
                        "items": {"bsonType": "string"},
                        "description": "List of preferred category names"
                    },
                    "receive_notifications": {"bsonType": "bool"}
                }
            },
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"}
        }
    }
}

EVENT_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "title",
            "description",
            "category",
            "organizer_id",
            "event_date",
            "total_capacity",
            "remaining_capacity",
            "price",
            "status"
        ],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "title": {
                "bsonType": "string",
                "minLength": 3,
                "maxLength": 150,
                "description": "Event title"
            },
            "description": {
                "bsonType": "string",
                "minLength": 10,
                "description": "Detailed description used for search & NLP classification"
            },
            "category": {
                "enum": [
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
                ],
                "description": "Primary category tag"
            },
            "tags": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
                "description": "Keyword tags for content-based similarity matching"
            },
            "organizer_id": {
                "bsonType": "objectId",
                "description": "Reference to the admin/organizer user document in users collection"
            },
            "organizer_name": {
                "bsonType": "string",
                "description": "Denormalized organizer name for fast retrieval"
            },
            "venue": {
                "bsonType": "object",
                "required": ["type", "name"],
                "description": "Embedded location/venue details",
                "properties": {
                    "type": {"enum": ["in-person", "online", "hybrid"]},
                    "name": {"bsonType": "string"},
                    "address_or_link": {"bsonType": "string"},
                    "city": {"bsonType": "string"}
                }
            },
            "event_date": {
                "bsonType": "date",
                "description": "Event schedule date and start time"
            },
            "duration_hours": {
                "bsonType": ["double", "int"],
                "minimum": 0.5
            },
            "total_capacity": {
                "bsonType": "int",
                "minimum": 1,
                "description": "Maximum attendees permitted"
            },
            "remaining_capacity": {
                "bsonType": "int",
                "minimum": 0,
                "description": "Remaining seats available"
            },
            "price": {
                "bsonType": ["double", "int"],
                "minimum": 0.0,
                "description": "Ticket price in INR (0.0 represents free entry)"
            },
            "status": {
                "enum": ["draft", "published", "cancelled", "completed"],
                "description": "Current lifecycle state"
            },
            "image_url": {"bsonType": "string"},
            "previous_event_date": {
                "bsonType": "date",
                "description": "Previous scheduled event date before rescheduling"
            },
            "rescheduled_at": {
                "bsonType": "date",
                "description": "Timestamp when the event was last rescheduled"
            },
            "reschedule_history": {
                "bsonType": "array",
                "items": {"bsonType": "object"},
                "description": "Audit trail of all reschedule operations"
            },
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"}
        }
    }
}

BOOKING_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "booking_code",
            "user_id",
            "event_id",
            "booking_date",
            "tickets_count",
            "total_amount",
            "status",
            "ticket_details"
        ],
        "properties": {
            "_id": {"bsonType": "objectId"},
            "booking_code": {
                "bsonType": "string",
                "description": "Unique human-readable alphanumeric code, e.g., EVT-2026-8942"
            },
            "user_id": {
                "bsonType": "objectId",
                "description": "Reference to attendee _id in users collection"
            },
            "event_id": {
                "bsonType": "objectId",
                "description": "Reference to event _id in events collection"
            },
            "booking_date": {"bsonType": "date"},
            "tickets_count": {
                "bsonType": "int",
                "minimum": 1,
                "maximum": 5,
                "description": "Number of seats booked in this transaction"
            },
            "total_amount": {
                "bsonType": ["double", "int"],
                "minimum": 0.0,
                "description": "Actual total monetary amount paid for this booking (tickets_count * price)"
            },
            "status": {
                "enum": ["confirmed", "cancelled", "checked_in"],
                "description": "Reservation status"
            },
            "ticket_details": {
                "bsonType": "object",
                "required": ["attendee_name", "attendee_email", "qr_payload"],
                "description": "Embedded ticket metadata",
                "properties": {
                    "attendee_name": {"bsonType": "string"},
                    "attendee_email": {"bsonType": "string"},
                    "qr_payload": {"bsonType": "string"},
                    "checked_in_at": {"bsonType": ["date", "null"]}
                }
            },
            "cancelled_at": {"bsonType": ["date", "null"]}
        }
    }
}
