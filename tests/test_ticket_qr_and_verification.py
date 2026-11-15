# tests/test_ticket_qr_and_verification.py
"""
Test Suite for EventSphere Genuine QR Code Generation,
Gate Verification, and Secure Admin Ticket Check-in.

Verifies:
1. Dynamic QR code PNG image generation via qrcode + Pillow.
2. QR payload encoding (booking_code|user_id|event_id).
3. Verification endpoint: returns verified: true and checked_in: false for confirmed ticket.
4. Access control: Unauthenticated (401) and Regular User (403) blocked from check-in.
5. Admin check-in: Valid admin successfully checks in ticket (200 OK), sets checked_in: true and timestamp.
6. Duplicate check-in prevention: repeated check-ins rejected with 409 Conflict.
7. Cancelled booking rejection: cancelled bookings rejected with 400 Bad Request.
8. Invalid / tampered QR payload rejection: malformed or mismatched user/event IDs rejected with 400.
9. Direct QR image endpoint ownership protection.
"""

import os
import sys
import base64
from datetime import datetime, timedelta
from bson import ObjectId

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from app.services.db import get_db, to_object_id
from app.services.booking_service import BookingService
from app.services.user_service import UserService

PNG_HEADER = b"\x89PNG\r\n\x1a\n"

def run_tests():
    app = create_app()
    with app.app_context():
        db = get_db()
        print("=" * 80)
        print("EVENTSPHERE DYNAMIC QR CODE & ADMIN TICKET CHECK-IN SECURITY SUITE")
        print("=" * 80)

        # -------------------------------------------------------------
        # TEST 1: QR Code Generation
        # -------------------------------------------------------------
        print("\n--- [Test 1] Generating Genuine QR Code PNG and Base64 Data URI ---")
        test_payload = "EVT-2026-TEST01|65a123456789abcdef012345|65a987654321fedcba543210"
        png_bytes = BookingService.generate_qr_code_bytes(test_payload)
        assert isinstance(png_bytes, bytes)
        assert len(png_bytes) > 100
        assert png_bytes.startswith(PNG_HEADER), "Generated file is not a valid PNG image!"

        b64_uri = BookingService.generate_qr_code_base64(test_payload)
        assert b64_uri.startswith("data:image/png;base64,")
        decoded = base64.b64decode(b64_uri.split(",")[1])
        assert decoded.startswith(PNG_HEADER)
        print(f"[PASS] Successfully generated valid PNG QR code ({len(png_bytes)} bytes) and Base64 URI.")

        # -------------------------------------------------------------
        # TEST 2: Unique QR Codes for Distinct Payloads
        # -------------------------------------------------------------
        print("\n--- [Test 2] Ensuring Unique QR Codes for Distinct Bookings ---")
        payload_a = "EVT-2026-AAA111|65a111111111111111111111|65a222222222222222222222"
        payload_b = "EVT-2026-BBB222|65a333333333333333333333|65a444444444444444444444"
        bytes_a = BookingService.generate_qr_code_bytes(payload_a)
        bytes_b = BookingService.generate_qr_code_bytes(payload_b)
        assert bytes_a != bytes_b, "Distinct booking payloads must generate different QR images!"
        print("[PASS] Distinct booking payloads produce unique QR codes.")

        # -------------------------------------------------------------
        # Setup Test Fixtures in MongoDB
        # -------------------------------------------------------------
        print("\n--- [Setup] Creating Test User, Event, and Bookings ---")
        admin_doc = db.users.find_one({"email": "admin@edusphere.in"})
        user_doc = db.users.find_one({"email": "user@edusphere.in"})
        assert admin_doc and user_doc, "Evaluation accounts not found. Run scripts/seed_demo_accounts.py first."

        user_id = str(user_doc["_id"])
        admin_id = str(admin_doc["_id"])

        # Authenticate sessions
        admin_client = app.test_client()
        with admin_client.session_transaction() as sess:
            sess["user_id"] = admin_id
            sess["user_name"] = admin_doc["name"]
            sess["email"] = admin_doc["email"]
            sess["role"] = "admin"

        user_client = app.test_client()
        with user_client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_name"] = user_doc["name"]
            sess["email"] = user_doc["email"]
            sess["role"] = "user"

        anon_client = app.test_client()

        # Create published test event
        now = datetime.utcnow()
        future_date = now + timedelta(days=14)
        test_event = {
            "title": "Cybersecurity & Cloud Summit 2026",
            "description": "Annual security and cloud technology summit.",
            "category": "Technology & Innovation",
            "venue": {
                "type": "in-person",
                "name": "Auditorium Prime",
                "city": "Bengaluru",
                "address_or_link": "Gate 3, Innovation Hub"
            },
            "event_date": future_date,
            "duration_hours": 4.0,
            "total_capacity": 100,
            "remaining_capacity": 96,
            "price": 500.0,
            "status": "published",
            "organizer_id": admin_doc["_id"],
            "created_at": now
        }
        event_res = db.events.insert_one(test_event)
        event_id = str(event_res.inserted_id)

        # Create confirmed test booking
        booking = BookingService.create_booking(
            user_id=user_id,
            event_id=event_id,
            tickets_count=2,
            attendee_name="Sample User Attendee",
            attendee_email="user@edusphere.in"
        )
        booking_id = str(booking["_id"])
        booking_code = booking["booking_code"]
        expected_payload = f"{booking_code}|{user_id}|{event_id}"

        print(f"[OK] Test Booking created: ID={booking_id}, Code={booking_code}")
        print(f"     Payload: {expected_payload}")

        # -------------------------------------------------------------
        # TEST 3: Verification Endpoint Returns verified: true, checked_in: false
        # -------------------------------------------------------------
        print("\n--- [Test 3] Verifying Ticket Returns verified: true and checked_in: false ---")
        res_verify = admin_client.post("/api/bookings/verify", json={"payload": expected_payload})
        assert res_verify.status_code == 200, f"Verification failed: {res_verify.data}"
        data_verify = res_verify.json
        assert data_verify["success"] is True
        assert data_verify["verified"] is True
        assert data_verify["checked_in"] is False, "Verification must not prematurely mark ticket as checked in!"
        assert data_verify["already_checked_in"] is False
        assert data_verify["status"] == "confirmed"
        assert data_verify["booking_code"] == booking_code
        assert data_verify["attendee_name"] == "Sample User Attendee"
        assert "Cybersecurity & Cloud Summit" in data_verify["event_title"]
        print("[PASS] Verification endpoint successfully verified ticket without altering checked_in status.")

        # -------------------------------------------------------------
        # TEST 4: Access Control on Ticket Check-In Endpoint
        # -------------------------------------------------------------
        print("\n--- [Test 4] Verifying RBAC Access Control on Check-in Endpoint ---")
        # 1. Unauthenticated request -> 401 Unauthorized
        res_anon_chk = anon_client.post("/api/bookings/check-in", json={"payload": expected_payload})
        assert res_anon_chk.status_code == 401, f"Expected 401 for unauthenticated check-in, got {res_anon_chk.status_code}"
        assert "Authentication required" in res_anon_chk.json["error"]
        print("[PASS] Unauthenticated check-in request strictly rejected with 401 Unauthorized.")

        # 2. Regular user (attendee) request -> 403 Forbidden
        res_user_chk = user_client.post("/api/bookings/check-in", json={"payload": expected_payload})
        assert res_user_chk.status_code == 403, f"Expected 403 for regular attendee check-in, got {res_user_chk.status_code}"
        assert "Admin privileges required" in res_user_chk.json["error"]
        print("[PASS] Regular user (attendee) check-in request strictly blocked with 403 Forbidden.")

        # -------------------------------------------------------------
        # TEST 5: Admin Successfully Checks In Verified Ticket
        # -------------------------------------------------------------
        print("\n--- [Test 5] Valid Admin Check-in (POST /api/bookings/check-in) ---")
        res_admin_chk = admin_client.post("/api/bookings/check-in", json={"payload": expected_payload})
        assert res_admin_chk.status_code == 200, f"Admin check-in failed: {res_admin_chk.data}"
        data_chk = res_admin_chk.json
        assert data_chk["success"] is True
        assert data_chk["checked_in"] is True
        assert data_chk["status"] == "checked_in"
        assert data_chk["checked_in_at"] is not None
        assert data_chk["booking_code"] == booking_code
        assert data_chk["attendee_name"] == "Sample User Attendee"
        assert data_chk["attendee_email"] == "user@edusphere.in"
        assert "Cybersecurity & Cloud Summit" in data_chk["event_title"]
        assert data_chk["event_venue"] == "Auditorium Prime"

        # Check database document updates: checked_in: true and checked_in_at timestamp
        doc_in_db = db.bookings.find_one({"_id": to_object_id(booking_id)})
        assert doc_in_db["checked_in"] is True, "Booking document 'checked_in' field must be True!"
        assert doc_in_db["checked_in_at"] is not None, "Booking document 'checked_in_at' must be set!"
        assert doc_in_db["status"] == "checked_in"
        assert doc_in_db["ticket_details"]["checked_in_at"] is not None
        print("[PASS] Valid admin check-in succeeded (HTTP 200). checked_in: true and checked_in_at recorded in MongoDB.")

        # -------------------------------------------------------------
        # TEST 6: Duplicate Check-in Prevention
        # -------------------------------------------------------------
        print("\n--- [Test 6] Duplicate Check-in Prevention (Repeated Scans) ---")
        res_dup = admin_client.post("/api/bookings/check-in", json={"payload": expected_payload})
        assert res_dup.status_code == 409, f"Expected 409 Conflict for duplicate check-in, got {res_dup.status_code}"
        data_dup = res_dup.json
        assert data_dup["checked_in"] is False
        assert data_dup["already_checked_in"] is True
        assert "DUPLICATE SCAN" in data_dup["error"] or "already been checked in" in data_dup["error"]
        print(f"[PASS] Duplicate check-in strictly rejected with 409 Conflict.")
        print(f"       Message: '{data_dup['error']}'")

        # Also verify verification endpoint detects already checked-in status
        res_verify_dup = admin_client.post("/api/bookings/verify", json={"payload": expected_payload})
        assert res_verify_dup.status_code == 409
        assert res_verify_dup.json["already_checked_in"] is True
        print("[PASS] Verification endpoint correctly returns 409 for already checked-in tickets.")

        # -------------------------------------------------------------
        # TEST 7: Rejection of Cancelled Bookings
        # -------------------------------------------------------------
        print("\n--- [Test 7] Rejecting Cancelled Bookings ---")
        booking_cancel = BookingService.create_booking(
            user_id=user_id,
            event_id=event_id,
            tickets_count=1,
            attendee_name="Cancel Test Attendee",
            attendee_email="user@edusphere.in"
        )
        cancel_id = str(booking_cancel["_id"])
        cancel_payload = f"{booking_cancel['booking_code']}|{user_id}|{event_id}"
        BookingService.cancel_booking(cancel_id, user_id=user_id)

        # Attempt check-in on cancelled ticket
        res_chk_cancel = admin_client.post("/api/bookings/check-in", json={"payload": cancel_payload})
        assert res_chk_cancel.status_code == 400
        assert res_chk_cancel.json["checked_in"] is False
        assert "cancelled" in res_chk_cancel.json["error"].lower()
        print("[PASS] Cancelled booking check-in strictly rejected with 400 Bad Request.")

        # -------------------------------------------------------------
        # TEST 8: Rejection of Malformed / Invalid QR Payloads
        # -------------------------------------------------------------
        print("\n--- [Test 8] Rejecting Malformed / Invalid QR Payloads ---")
        # Empty payload
        res_empty = admin_client.post("/api/bookings/check-in", json={"payload": ""})
        assert res_empty.status_code == 400
        assert res_empty.json["checked_in"] is False

        # Missing pipes
        res_no_pipe = admin_client.post("/api/bookings/check-in", json={"payload": "InvalidPayloadNoPipes"})
        assert res_no_pipe.status_code == 400
        assert res_no_pipe.json["checked_in"] is False
        assert "format" in res_no_pipe.json["error"].lower()

        # Malformed hexadecimal ObjectIds
        res_bad_hex = admin_client.post("/api/bookings/check-in", json={"payload": f"{booking_code}|not-hex|not-hex"})
        assert res_bad_hex.status_code == 400
        assert res_bad_hex.json["checked_in"] is False
        print("[PASS] Malformed payloads correctly rejected with 400 Bad Request.")

        # -------------------------------------------------------------
        # TEST 9: Rejection of Non-Existent Booking
        # -------------------------------------------------------------
        print("\n--- [Test 9] Rejecting Non-Existent Booking Code ---")
        fake_payload = f"EVT-2026-NONEXIST|{user_id}|{event_id}"
        res_fake = admin_client.post("/api/bookings/check-in", json={"payload": fake_payload})
        assert res_fake.status_code in [400, 404]
        assert res_fake.json["checked_in"] is False
        assert "No booking found" in res_fake.json["error"]
        print("[PASS] Non-existent booking code rejected with 404/400.")

        # -------------------------------------------------------------
        # TEST 10: Rejection of Tampered / Mismatched User & Event Identifiers
        # -------------------------------------------------------------
        print("\n--- [Test 10] Rejecting Tampered / Mismatched User & Event Identifiers ---")
        # Create fresh confirmed booking for tamper testing
        booking_tamper = BookingService.create_booking(
            user_id=user_id,
            event_id=event_id,
            tickets_count=1,
            attendee_name="Tamper Test Attendee",
            attendee_email="user@edusphere.in"
        )
        tamper_code = booking_tamper["booking_code"]

        other_user_id = str(ObjectId())
        res_tamper_u = admin_client.post("/api/bookings/check-in", json={"payload": f"{tamper_code}|{other_user_id}|{event_id}"})
        assert res_tamper_u.status_code == 400
        assert res_tamper_u.json["checked_in"] is False
        assert "User identifier mismatch" in res_tamper_u.json["error"]

        other_event_id = str(ObjectId())
        res_tamper_e = admin_client.post("/api/bookings/check-in", json={"payload": f"{tamper_code}|{user_id}|{other_event_id}"})
        assert res_tamper_e.status_code == 400
        assert res_tamper_e.json["checked_in"] is False
        assert "Event identifier mismatch" in res_tamper_e.json["error"]
        print("[PASS] Mismatched user and event identifiers strictly rejected with 400 Bad Request.")

        # -------------------------------------------------------------
        # TEST 11: Direct QR Image Access Control (GET /api/bookings/<id>/qr)
        # -------------------------------------------------------------
        print("\n--- [Test 11] Verifying QR Image Endpoint Access Control ---")
        res_qr_anon = anon_client.get(f"/api/bookings/{booking_id}/qr")
        assert res_qr_anon.status_code == 401

        res_qr_owner = user_client.get(f"/api/bookings/{booking_id}/qr")
        assert res_qr_owner.status_code == 200
        assert res_qr_owner.content_type == "image/png"
        assert res_qr_owner.data.startswith(PNG_HEADER)

        res_qr_admin = admin_client.get(f"/api/bookings/{booking_id}/qr")
        assert res_qr_admin.status_code == 200
        assert res_qr_admin.content_type == "image/png"
        print("[PASS] Direct QR image endpoint strictly protected: 401 for unauthenticated, 200 for owner/admin.")

        # -------------------------------------------------------------
        # Cleanup Test Artifacts
        # -------------------------------------------------------------
        print("\nCleaning up test artifacts from MongoDB Atlas...")
        db.bookings.delete_many({"event_id": to_object_id(event_id)})
        db.events.delete_one({"_id": to_object_id(event_id)})
        print("[OK] Test bookings and event cleaned up. Database remains clean.")

        print("\n" + "=" * 80)
        print("ALL QR VERIFICATION & CHECK-IN SECURITY TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 80)

if __name__ == "__main__":
    run_tests()
