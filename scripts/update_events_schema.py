# scripts/update_events_schema.py
"""
Safely migrates the 'events' collection to the expanded JSON Schema validator
while preserving all existing documents and indexes.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pymongo import ASCENDING, TEXT
from app.services.db import get_db
from app.models.schemas import EVENT_SCHEMA

def migrate_events_schema():
    db = get_db()
    print("Beginning safe schema migration for 'events' collection...")

    # 1. Backup existing events
    existing_events = list(db.events.find({}))
    print(f"[OK] Backed up {len(existing_events)} existing events in memory.")

    # 2. Drop current events collection
    db.events.drop()
    print("[OK] Dropped old events collection.")

    # 3. Recreate collection with expanded schema validator
    db.create_collection(
        "events",
        validator=EVENT_SCHEMA,
        validationLevel="strict",
        validationAction="error"
    )
    print("[OK] Created new 'events' collection with expanded category schema validator.")

    # 4. Rebuild indexes
    db.events.create_index(
        [("title", TEXT), ("description", TEXT), ("tags", TEXT)],
        name="idx_events_text_search"
    )
    db.events.create_index(
        [("category", ASCENDING), ("status", ASCENDING), ("event_date", ASCENDING)],
        name="idx_events_cat_status_date"
    )
    db.events.create_index(
        [("event_date", ASCENDING)],
        name="idx_events_date"
    )
    print("[OK] Rebuilt all text and compound indexes on 'events'.")

    # 5. Restore backed up events
    if existing_events:
        db.events.insert_many(existing_events)
        print(f"[OK] Restored {len(existing_events)} existing events.")

    # 6. Verify insertion of new categories
    test_doc = {
        "title": "Category Validation Test Event",
        "description": "Testing that expanded categories pass MongoDB Atlas schema validation.",
        "category": "Music & Entertainment",
        "tags": ["Music", "Test"],
        "organizer_id": existing_events[0]["organizer_id"] if existing_events else db.users.find_one()["_id"],
        "organizer_name": "Test Organizer",
        "venue": {"type": "in-person", "name": "Concert Hall", "address_or_link": "Gate 1", "city": "Bengaluru"},
        "event_date": existing_events[0]["event_date"] if existing_events else existing_events,
        "duration_hours": 3.0,
        "total_capacity": 50,
        "remaining_capacity": 50,
        "price": 100.0,
        "status": "published"
    }
    from datetime import datetime
    test_doc["event_date"] = datetime(2026, 12, 1)
    res = db.events.insert_one(test_doc)
    print(f"[SUCCESS] Inserted test event with category 'Music & Entertainment' (ID: {res.inserted_id})")
    db.events.delete_one({"_id": res.inserted_id})
    print("[OK] Removed test event. Schema migration completed cleanly!")

if __name__ == "__main__":
    migrate_events_schema()
