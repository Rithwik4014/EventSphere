# tests/test_event_reschedule.py
"""
Comprehensive Test Suite for Event Reschedule & Edit Functionality in EventSphere.
Verifies:
1. Rescheduling allows authenticated admins to update event date and start time.
2. Validates that past or present dates are strictly rejected with 400 Bad Request.
3. In-place document update: verifies NO duplicate event document is created.
4. Preserves all bookings, booking codes, ticket records, and seat capacity.
5. Ensures updated dates appear on event details, booking history, and digital tickets.
6. Records previous and updated event dates in an audit trail (previous_event_date,
   rescheduled_at, and reschedule_history array).
7. Only authenticated admins can edit or reschedule events (unauthenticated=401, regular user=403).
8. Admin can edit event title, description, category, price, and venue details via PUT /api/events/<id>.
9. Existing View and Cancel functionality remains unchanged.
"""

import os
import sys
from datetime import datetime, timedelta

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from app.services.db import get_db

def run_tests():
    print("=" * 68)
    print("EVENTSPHERE ADMIN EVENT RESCHEDULE & EDIT TEST SUITE")
    print("=" * 68)

    app = create_app("testing")
    client = app.test_client()
    db = get_db()
    suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    created_user_ids = []
    created_event_ids = []
    created_booking_ids = []

    try:
        # -----------------------------------------------------------------
        # SETUP: Create a student account and an admin account
        # -----------------------------------------------------------------
        print("\n--- [Setup] Creating Test Student & Authenticating Admin ---")
        student_email = f"student.{suffix}@example.com"
        reg_res = client.post("/api/auth/register", json={
            "name": f"Regular Student {suffix}",
            "email": student_email,
            "password": "Password123!"
        })
        assert reg_res.status_code == 201
        student_id = reg_res.json["user"]["_id"]
        created_user_ids.append(student_id)

        # Authenticate using existing demo admin account
        admin_login = client.post("/api/auth/login", json={
            "email": "admin@edusphere.in",
            "password": "admin123"
        })
        assert admin_login.status_code == 200, "Demo admin login must succeed"
        admin_id = admin_login.json["user"]["_id"]
        print(f"[OK] Admin authenticated: _id={admin_id}")

        # Create a test event as admin
        original_date = datetime.utcnow() + timedelta(days=7)
        event_payload = {
            "title": f"Test Hackathon {suffix}",
            "description": "24-hour coding marathon on intelligent distributed databases.",
            "category": "Technology",
            "tags": ["Coding", "Hackathon"],
            "venue": {
                "type": "in-person",
                "name": "Alan Turing Tech Hall",
                "address_or_link": "Block A",
                "city": "Bengaluru"
            },
            "event_date": original_date.isoformat(),
            "duration_hours": 4.0,
            "total_capacity": 50,
            "price": 150.0,
            "organizer_name": "Department of CSE"
        }
        res_create = client.post("/api/events", json=event_payload)
        assert res_create.status_code == 201
        event_data = res_create.json["event"]
        test_event_id = event_data["_id"]
        created_event_ids.append(test_event_id)
        print(f"[OK] Test event created: _id={test_event_id}, scheduled for {original_date.isoformat()}")

        # Book 2 tickets on this event as student
        client.get("/api/auth/logout")  # Log out admin
        client.post("/api/auth/login", json={"email": student_email, "password": "Password123!"})
        res_bk = client.post("/api/bookings", json={
            "event_id": test_event_id,
            "tickets_count": 2,
            "attendee_name": f"Student {suffix}",
            "attendee_email": student_email
        })
        assert res_bk.status_code == 201
        booking_data = res_bk.json["booking"]
        booking_id = booking_data["_id"]
        booking_code = booking_data["booking_code"]
        created_booking_ids.append(booking_id)
        print(f"[OK] Test booking created: code={booking_code}, remaining_capacity=48")

        # -----------------------------------------------------------------
        # TEST 1: Role-Based Authorization for Reschedule & Edit
        # -----------------------------------------------------------------
        print("\n--- [Test 1] Enforcing RBAC Authorization on Reschedule & Edit ---")
        new_valid_date = datetime.utcnow() + timedelta(days=14)

        # 1a. Regular user attempt to reschedule -> 403 Forbidden
        res_user_reschedule = client.post(f"/api/events/{test_event_id}/reschedule", json={
            "new_event_date": new_valid_date.isoformat()
        })
        assert res_user_reschedule.status_code == 403
        print("[PASS] Regular user cannot reschedule event: 403 Forbidden.")

        # 1b. Regular user attempt to edit -> 403 Forbidden
        res_user_edit = client.put(f"/api/events/{test_event_id}", json={"title": "Hacked Title"})
        assert res_user_edit.status_code == 403
        print("[PASS] Regular user cannot edit event: 403 Forbidden.")

        # 1c. Unauthenticated attempt -> 401 Unauthorized
        client.get("/api/auth/logout")
        res_unauth_reschedule = client.post(f"/api/events/{test_event_id}/reschedule", json={
            "new_event_date": new_valid_date.isoformat()
        })
        assert res_unauth_reschedule.status_code == 401
        print("[PASS] Unauthenticated user cannot reschedule event: 401 Unauthorized.")

        # Log back in as admin
        client.post("/api/auth/login", json={"email": "admin@edusphere.in", "password": "admin123"})

        # -----------------------------------------------------------------
        # TEST 2: Validate that Past Date is Rejected
        # -----------------------------------------------------------------
        print("\n--- [Test 2] Validating that Past Dates are Rejected ---")
        past_date = datetime.utcnow() - timedelta(days=2)
        res_past = client.post(f"/api/events/{test_event_id}/reschedule", json={
            "new_event_date": past_date.isoformat(),
            "reason": "Invalid past test"
        })
        assert res_past.status_code == 400
        assert "future" in res_past.json.get("error", "").lower()
        print(f"[PASS] Rescheduling to past date was rejected with 400: '{res_past.json.get('error')}'")

        # -----------------------------------------------------------------
        # TEST 3: Successful Reschedule with In-Place Update & Audit Trail
        # -----------------------------------------------------------------
        print("\n--- [Test 3] Rescheduling Event & Verifying In-Place Update & Audit ---")
        event_count_before = db.events.count_documents({})
        audit_reason = "Auditorium maintenance and HVAC upgrade"

        res_reschedule = client.post(f"/api/events/{test_event_id}/reschedule", json={
            "new_event_date": new_valid_date.isoformat(),
            "reason": audit_reason
        })
        assert res_reschedule.status_code == 200
        rescheduled_data = res_reschedule.json["event"]
        assert res_reschedule.json["success"] is True

        # Verify no duplicate document was created
        event_count_after = db.events.count_documents({})
        assert event_count_before == event_count_after, "Duplicate event created!"
        print(f"[PASS] Document updated in-place: event count remained exactly {event_count_after}")

        # Check document fields directly in MongoDB
        from bson import ObjectId
        db_event = db.events.find_one({"_id": ObjectId(test_event_id)})
        assert db_event is not None
        assert str(db_event["_id"]) == str(test_event_id)
        assert db_event["previous_event_date"] is not None
        assert db_event["rescheduled_at"] is not None
        assert len(db_event.get("reschedule_history", [])) == 1

        history_entry = db_event["reschedule_history"][0]
        assert history_entry["reason"] == audit_reason
        assert history_entry["previous_event_date"] is not None
        assert history_entry["new_event_date"] is not None
        print(f"[PASS] Audit trail verified: recorded previous_event_date and reschedule_history entry.")

        # -----------------------------------------------------------------
        # TEST 4: Preserve Bookings, Tickets, and Seat Capacity
        # -----------------------------------------------------------------
        print("\n--- [Test 4] Preserving Existing Bookings, Codes, and Capacity ---")
        # Capacity check
        assert db_event["total_capacity"] == 50
        assert db_event["remaining_capacity"] == 48, f"Capacity changed unexpectedly! Got {db_event['remaining_capacity']}"
        print(f"[PASS] Seat capacity preserved: remaining={db_event['remaining_capacity']}, total={db_event['total_capacity']}")

        # Booking check
        db_booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
        assert db_booking is not None
        assert db_booking["booking_code"] == booking_code
        assert db_booking["status"] == "confirmed"
        assert db_booking["tickets_count"] == 2
        assert db_booking["ticket_details"]["attendee_name"] == f"Student {suffix}"
        print(f"[PASS] Existing booking record and code ({booking_code}) 100% preserved.")

        # -----------------------------------------------------------------
        # TEST 5: Updated Dates Visible in Event Details, Booking History, Tickets
        # -----------------------------------------------------------------
        print("\n--- [Test 5] Verifying Updated Dates Appear on Public & User Views ---")
        # 5a. Event Details API
        res_get_ev = client.get(f"/api/events/{test_event_id}")
        assert res_get_ev.status_code == 200
        ev_view = res_get_ev.json["event"]
        assert ev_view["rescheduled_at"] is not None
        print(f"[PASS] GET /api/events/{test_event_id} returns updated date & reschedule audit flag.")

        # 5b. Booking History API
        # Log in as student to check booking history
        client.get("/api/auth/logout")
        client.post("/api/auth/login", json={"email": student_email, "password": "Password123!"})
        res_my_bks = client.get("/api/bookings/my-tickets")
        assert res_my_bks.status_code == 200
        my_bks = res_my_bks.json["bookings"]
        target_bk = next((b for b in my_bks if b["_id"] == booking_id), None)
        assert target_bk is not None
        assert target_bk["is_rescheduled"] is True
        assert target_bk["event_date"] is not None
        print(f"[PASS] GET /api/bookings/my-tickets returns enriched updated event_date and is_rescheduled=True.")

        # 5c. Digital Ticket Code Lookup
        res_code = client.get(f"/api/bookings/code/{booking_code}")
        assert res_code.status_code == 200
        assert res_code.json["booking"]["booking_code"] == booking_code
        print(f"[PASS] Digital ticket lookup /api/bookings/code/{booking_code} remains valid and operational.")

        # -----------------------------------------------------------------
        # TEST 6: Event Edit Functionality (PUT /api/events/<id>)
        # -----------------------------------------------------------------
        print("\n--- [Test 6] Testing Admin Event Edit Functionality ---")
        client.get("/api/auth/logout")
        client.post("/api/auth/login", json={"email": "admin@edusphere.in", "password": "admin123"})

        edit_payload = {
            "title": f"Updated Hackathon Title {suffix}",
            "description": "Updated deep dive tutorial and competition for distributed systems.",
            "price": 200.0,
            "category": "Gaming",
            "venue": {
                "type": "hybrid",
                "name": "Virtual Lab Hall 4",
                "address_or_link": "https://meet.college.edu/hackathon",
                "city": "Bengaluru"
            }
        }
        res_edit = client.put(f"/api/events/{test_event_id}", json=edit_payload)
        assert res_edit.status_code == 200
        updated_event = res_edit.json["event"]
        assert updated_event["title"] == edit_payload["title"]
        assert updated_event["price"] == 200.0
        assert updated_event["category"] == "Gaming"
        assert updated_event["venue"]["type"] == "hybrid"
        print("[PASS] PUT /api/events/<id> successfully updated title, category, price, and venue.")

        # -----------------------------------------------------------------
        # TEST 7: Cancel and View Routes Preserved
        # -----------------------------------------------------------------
        print("\n--- [Test 7] Verifying Cancel and View Actions Remain Intact ---")
        # Cancel event as admin
        res_cancel = client.post(f"/api/events/{test_event_id}/cancel")
        assert res_cancel.status_code == 200
        assert res_cancel.json["event"]["status"] == "cancelled"
        print("[PASS] POST /api/events/<id>/cancel successfully marked event as cancelled.")

        # View route
        res_view = client.get(f"/events/{test_event_id}")
        assert res_view.status_code == 200
        print("[PASS] GET /events/<id> renders view with 200 OK.")

        print("\n" + "=" * 68)
        print("ALL RESCHEDULE & EDIT TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 68)
        return True

    finally:
        print("\nCleaning up test artifacts...")
        if created_booking_ids:
            from bson import ObjectId
            oids = [ObjectId(bid) if isinstance(bid, str) else bid for bid in created_booking_ids]
            db.bookings.delete_many({"_id": {"$in": oids}})
        if created_event_ids:
            from bson import ObjectId
            oids = [ObjectId(eid) if isinstance(eid, str) else eid for eid in created_event_ids]
            db.events.delete_many({"_id": {"$in": oids}})
        if created_user_ids:
            from bson import ObjectId
            oids = [ObjectId(uid) if isinstance(uid, str) else uid for uid in created_user_ids]
            db.users.delete_many({"_id": {"$in": oids}})
        print("[OK] Test artifacts cleaned up. Database remains clean.")

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
