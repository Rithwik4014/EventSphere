# tests/test_crud.py
"""
CRUD Operations Verification Suite for EventSphere.
Demonstrates Insert, Read, Update, Delete for:
- users collection
- events collection
- bookings collection (including multi-document ACID transactions)
Verifies error handling for duplicate keys, schema violations, and invalid ObjectIds.
Cleans up test records upon completion.
"""

import os
import sys
from datetime import datetime, timedelta

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.db import get_client, get_db, to_object_id
from app.services.user_service import UserService
from app.services.event_service import EventService
from app.services.booking_service import BookingService

def run_tests():
    print("=" * 60)
    print("EVENTSPHERE CRUD OPERATIONS TEST SUITE")
    print("=" * 60)

    test_user_id = None
    test_organizer_id = None
    test_event_id = None
    test_booking_id = None

    try:
        # =====================================================================
        # 1. USER CRUD TESTS
        # =====================================================================
        print("\n--- [1/3] TESTING USERS COLLECTION CRUD ---")

        # 1a. Create User (Insert)
        unique_suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        test_email = f"test.student.{unique_suffix}@college.edu"
        user = UserService.create_user(
            name="Test Student",
            email=test_email,
            password_hash="scrypt:mock-hashed-password-12345",
            role="user",
            preferences={
                "favorite_categories": ["Technology", "Workshop"],
                "receive_notifications": True
            }
        )
        test_user_id = user["_id"]
        print(f"[PASS] User Inserted: _id={test_user_id}, email={user['email']}")

        # 1b. Duplicate Email Error Handling
        try:
            UserService.create_user(
                name="Duplicate Student",
                email=test_email,
                password_hash="scrypt:different-hash",
                role="user"
            )
            print("[FAIL] Duplicate email did not raise error!")
        except ValueError as e:
            print(f"[PASS] Duplicate Email Blocked: {e}")

        # 1c. Schema Validation Error Handling (invalid email pattern & missing fields)
        try:
            # Bypass UserService helper and try direct raw insert violating regex & types
            get_db().users.insert_one({
                "name": "Invalid User",
                "email": "not-an-email",
                "password_hash": "scrypt:hash",
                "role": "non_existent_role",
                "created_at": datetime.utcnow()
            })
            print("[FAIL] Schema validator failed to block invalid user document!")
        except Exception as e:
            print(f"[PASS] Schema Validation Blocked Invalid User: Type={type(e).__name__}")

        # 1d. Read User (Find by ID & Email)
        found_by_id = UserService.get_user_by_id(test_user_id)
        assert found_by_id is not None, "User should be found by ID"
        found_by_email = UserService.get_user_by_email(test_email)
        assert found_by_email is not None, "User should be found by email"
        print(f"[PASS] User Read: Found '{found_by_id['name']}' by ID and email.")

        # 1e. Update User
        updated_user = UserService.update_user(
            test_user_id,
            {"name": "Test Student Updated", "preferences.receive_notifications": False}
        )
        assert updated_user["name"] == "Test Student Updated"
        print(f"[PASS] User Updated: New Name='{updated_user['name']}'")

        # Create Organizer User for Event tests
        organizer = UserService.create_user(
            name="CS Faculty Organizer",
            email=f"org.{unique_suffix}@college.edu",
            password_hash="scrypt:mock-hash-org",
            role="admin"
        )
        test_organizer_id = organizer["_id"]

        # =====================================================================
        # 2. EVENT CRUD TESTS
        # =====================================================================
        print("\n--- [2/3] TESTING EVENTS COLLECTION CRUD ---")

        # 2a. Create Event (Insert)
        event_date = datetime.utcnow() + timedelta(days=14)
        event = EventService.create_event(
            title=f"AI & NoSQL Hackathon {unique_suffix}",
            description="A 24-hour collegiate hackathon exploring MongoDB Atlas aggregation pipelines and PyMongo integrations.",
            category="Technology",
            organizer_id=test_organizer_id,
            organizer_name="CS Faculty",
            venue={
                "type": "in-person",
                "name": "Tech Auditorium Block A",
                "address_or_link": "Campus Road 1",
                "city": "Bengaluru"
            },
            event_date=event_date,
            duration_hours=24.0,
            total_capacity=10,  # Small capacity to test saturation
            price=150.0,
            tags=["AI", "MongoDB", "NoSQL", "Hackathon"]
        )
        test_event_id = event["_id"]
        assert event["remaining_capacity"] == 10
        print(f"[PASS] Event Inserted: _id={test_event_id}, title='{event['title']}', capacity={event['remaining_capacity']}")

        # 2b. Schema Validation Error Handling (invalid category)
        try:
            EventService.create_event(
                title="Bad Category Event",
                description="Testing schema rejection for bad category",
                category="NonExistentCategory",
                organizer_id=test_organizer_id,
                organizer_name="CS Faculty",
                venue={"type": "in-person", "name": "Hall 1"},
                event_date=event_date,
                duration_hours=2.0,
                total_capacity=50
            )
            print("[FAIL] Invalid category was not rejected!")
        except ValueError as e:
            print(f"[PASS] Schema Validation Blocked Invalid Category: {e}")

        # 2c. Read & Query Events
        found_event = EventService.get_event_by_id(test_event_id)
        assert found_event is not None
        catalog = EventService.list_events(category="Technology", limit=10)
        assert len(catalog) >= 1
        print(f"[PASS] Event Read: Retrieved event by ID; Catalog query returned {len(catalog)} item(s).")

        # 2d. Full-Text Search
        search_res = EventService.search_events("Hackathon")
        assert len(search_res) >= 1, "Text search should return hackathon event"
        print(f"[PASS] Full-Text Search: Query 'Hackathon' matched {len(search_res)} event(s) via text index.")

        # 2e. Update Event
        updated_event = EventService.update_event(
            test_event_id,
            {"description": "Updated event description with enhanced prize pool details."}
        )
        assert "enhanced prize pool" in updated_event["description"]
        print("[PASS] Event Updated: Description successfully modified.")

        # =====================================================================
        # 3. BOOKING CRUD & TRANSACTION TESTS
        # =====================================================================
        print("\n--- [3/3] TESTING BOOKINGS COLLECTION CRUD & ACID TRANSACTIONS ---")

        # 3a. Create Booking (ACID Transaction with Capacity Decrement)
        booking = BookingService.create_booking(
            user_id=test_user_id,
            event_id=test_event_id,
            tickets_count=3,
            attendee_name="Test Student",
            attendee_email=test_email
        )
        test_booking_id = booking["_id"]
        booking_code = booking["booking_code"]

        # Verify event capacity decremented in DB from 10 to 7
        event_after_booking = EventService.get_event_by_id(test_event_id)
        assert event_after_booking["remaining_capacity"] == 7
        assert booking["total_amount"] == 3 * 150.0  # 450.0
        print(f"[PASS] Transactional Booking Created: Code={booking_code}, Amount=₹{booking['total_amount']}")
        print(f"[PASS] Atomic Capacity Check: Remaining capacity decremented from 10 to {event_after_booking['remaining_capacity']}")

        # 3b. Capacity Limit / Overselling Prevention (Transaction Abort)
        try:
            # Remaining is 7; attempt to book 5 (allowed count), then another 5 should fail,
            # or try booking 5 when remaining is only 2.
            # Let's attempt to book 8 tickets (which exceeds remaining 7 and exceeds single transaction limit 5)
            # First test: tickets_count > 5
            BookingService.create_booking(
                user_id=test_user_id,
                event_id=test_event_id,
                tickets_count=8,
                attendee_name="Test Student",
                attendee_email=test_email
            )
            print("[FAIL] Ticket count > 5 was not blocked!")
        except ValueError as e:
            print(f"[PASS] Single Transaction Max Ticket Limit (1-5) Enforced: {e}")

        # Now test capacity exhaustion: book 5 more (remaining becomes 2), then attempt booking 3 (should fail & abort)
        b2 = BookingService.create_booking(
            user_id=test_user_id,
            event_id=test_event_id,
            tickets_count=5,
            attendee_name="Test Student",
            attendee_email=test_email
        )
        event_after_b2 = EventService.get_event_by_id(test_event_id)
        assert event_after_b2["remaining_capacity"] == 2
        print(f"[PASS] Second Booking Succeeded: Remaining capacity is now {event_after_b2['remaining_capacity']}")

        # Now attempt booking 3 when only 2 remain -> must abort and leave capacity at 2
        try:
            BookingService.create_booking(
                user_id=test_user_id,
                event_id=test_event_id,
                tickets_count=3,
                attendee_name="Test Student",
                attendee_email=test_email
            )
            print("[FAIL] Transaction did not abort when capacity was insufficient!")
        except ValueError as e:
            print(f"[PASS] Transaction Aborted on Insufficient Capacity: {e}")

        # Verify capacity is still strictly 2
        event_after_abort = EventService.get_event_by_id(test_event_id)
        assert event_after_abort["remaining_capacity"] == 2
        print("[PASS] Post-Abort State Verified: Capacity remains unchanged at 2.")

        # Clean up second booking
        BookingService.delete_booking(b2["_id"])
        # Restore the 5 seats manually for clean state
        get_db().events.update_one({"_id": test_event_id}, {"$inc": {"remaining_capacity": 5}})

        # 3c. Read Booking (Find by ID & Code)
        found_booking = BookingService.get_booking_by_id(test_booking_id)
        assert found_booking is not None
        found_by_code = BookingService.get_booking_by_code(booking_code)
        assert found_by_code is not None
        user_bookings = BookingService.get_user_bookings(test_user_id)
        assert len(user_bookings) >= 1
        print(f"[PASS] Booking Read: Found by ID, Code, and User Query.")

        # 3d. Check-in Booking (Update)
        checked_in = BookingService.check_in_booking(test_booking_id)
        assert checked_in["status"] == "checked_in"
        assert checked_in["ticket_details"]["checked_in_at"] is not None
        print(f"[PASS] Booking Check-In: Status='{checked_in['status']}', Timestamp={checked_in['ticket_details']['checked_in_at']}")

        # 3e. Cancel Booking (ACID Transaction with Capacity Restock)
        # Reset status back to confirmed for cancellation test
        get_db().bookings.update_one({"_id": test_booking_id}, {"$set": {"status": "confirmed"}})
        # Capacity before cancel is 7
        cap_before_cancel = EventService.get_event_by_id(test_event_id)["remaining_capacity"]
        assert cap_before_cancel == 7

        cancelled = BookingService.cancel_booking(test_booking_id, user_id=test_user_id)
        assert cancelled is True
        b_after_cancel = BookingService.get_booking_by_id(test_booking_id)
        assert b_after_cancel["status"] == "cancelled"
        assert b_after_cancel["cancelled_at"] is not None

        # Verify capacity restored from 7 back to 10
        cap_after_cancel = EventService.get_event_by_id(test_event_id)["remaining_capacity"]
        assert cap_after_cancel == 10
        print(f"[PASS] Transactional Cancellation: Status='cancelled', Capacity restored from {cap_before_cancel} back to {cap_after_cancel}.")

        # 4. OBJECTID ERROR HANDLING TEST
        print("\n--- [4/4] TESTING OBJECTID VALIDATION ---")
        try:
            UserService.get_user_by_id("invalid-non-hex-id")
            print("[FAIL] Invalid ObjectId string was not rejected!")
        except ValueError as e:
            print(f"[PASS] Invalid ObjectId Correctly Rejected: {e}")

        print("\n" + "=" * 60)
        print("ALL CRUD & TRANSACTION TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)
        return True

    finally:
        # =====================================================================
        # CLEANUP: Remove Test Documents
        # =====================================================================
        print("\nCleaning up test documents from MongoDB Atlas...")
        db = get_db()
        if test_booking_id:
            db.bookings.delete_one({"_id": test_booking_id})
        if test_event_id:
            db.events.delete_one({"_id": test_event_id})
        if test_user_id:
            db.users.delete_one({"_id": test_user_id})
        if test_organizer_id:
            db.users.delete_one({"_id": test_organizer_id})
        print("[OK] Test artifacts cleaned up. Database remains clean.")

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
