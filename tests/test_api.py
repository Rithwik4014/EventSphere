# tests/test_api.py
"""
Flask Backend API Test Suite for EventSphere.
Verifies routes across:
- Root & Healthcheck
- Auth Blueprint (/api/auth)
- Events Blueprint (/api/events)
- Bookings Blueprint (/api/bookings)
- Admin Blueprint (/api/admin)
Uses Flask test_client and cleans up test records in MongoDB.
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from app.services.db import get_db

def run_api_tests():
    print("=" * 65)
    print("EVENTSPHERE FLASK API FOUNDATION TEST SUITE")
    print("=" * 65)

    app = create_app("testing")
    client = app.test_client()
    db = get_db()

    suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    user_email = f"api.student.{suffix}@college.edu"
    admin_email = f"api.admin.{suffix}@college.edu"

    test_user_id = None
    test_admin_id = None
    test_event_id = None
    test_booking_id = None

    try:
        # -------------------------------------------------------------
        # 1. ROOT & HEALTHCHECK
        # -------------------------------------------------------------
        print("\n--- [1/5] Testing Root & Healthcheck Endpoints ---")
        res_root = client.get("/")
        assert res_root.status_code == 200
        assert "EventSphere" in res_root.data.decode("utf-8")
        print("[PASS] GET / -> 200 (Home Page HTML Rendered)")

        res_health = client.get("/api/health")
        assert res_health.status_code == 200
        assert res_health.json["status"] == "healthy"
        assert res_health.json["database"] == "connected"
        print("[PASS] GET /api/health -> 200 (Database Connected)")

        # -------------------------------------------------------------
        # 2. AUTHENTICATION BLUEPRINT
        # -------------------------------------------------------------
        print("\n--- [2/5] Testing Authentication Endpoints (/api/auth) ---")

        # 2a. Register Student User
        reg_payload = {
            "name": f"Student {suffix}",
            "email": user_email,
            "password": "Password123!",
            "role": "user",
            "preferences": {"favorite_categories": ["Technology"]}
        }
        res_reg = client.post("/api/auth/register", json=reg_payload)
        assert res_reg.status_code == 201
        test_user_id = res_reg.json["user"]["_id"]
        assert "password_hash" not in res_reg.json["user"]
        print(f"[PASS] POST /api/auth/register -> 201 (Created user _id={test_user_id})")

        # 2b. Register User and verify role defaults to 'user' even when 'admin' requested
        admin_payload = {
            "name": f"Admin {suffix}",
            "email": admin_email,
            "password": "AdminPassword123!",
            "role": "admin"
        }
        res_admin_reg = client.post("/api/auth/register", json=admin_payload)
        assert res_admin_reg.status_code == 201
        test_admin_id = res_admin_reg.json["user"]["_id"]
        assert res_admin_reg.json["user"]["role"] == "user"
        print(f"[PASS] POST /api/auth/register strictly assigned role='user' (Exploit prevented)")

        # Promote test_admin_id for downstream admin endpoint testing
        from app.services.user_service import UserService
        UserService.update_user(test_admin_id, {"role": "admin"})
        print(f"[PASS] Promoted test account _id={test_admin_id} to admin for downstream API tests")

        # 2c. Duplicate registration rejection
        res_dup = client.post("/api/auth/register", json=reg_payload)
        assert res_dup.status_code == 400
        print("[PASS] POST /api/auth/register (Duplicate Email) -> 400 (Rejected)")

        # 2d. Login (Invalid credentials)
        res_bad_login = client.post("/api/auth/login", json={"email": user_email, "password": "WrongPassword"})
        assert res_bad_login.status_code == 401
        print("[PASS] POST /api/auth/login (Wrong Password) -> 401 (Unauthorized)")

        # 2e. Login (Valid credentials)
        res_login = client.post("/api/auth/login", json={"email": user_email, "password": "Password123!"})
        assert res_login.status_code == 200
        assert res_login.json["user"]["email"] == user_email
        print("[PASS] POST /api/auth/login (Valid) -> 200 (Session Created)")

        # 2f. Get Profile (Session Authenticated)
        res_prof = client.get("/api/auth/profile")
        assert res_prof.status_code == 200
        assert res_prof.json["user"]["email"] == user_email
        print("[PASS] GET /api/auth/profile -> 200 (Profile Retrieved)")

        # 2g. Update Profile Preferences
        res_upd_prof = client.put("/api/auth/profile", json={"preferences": {"favorite_categories": ["Workshop", "Gaming"]}})
        assert res_upd_prof.status_code == 200
        print("[PASS] PUT /api/auth/profile -> 200 (Preferences Updated)")

        # -------------------------------------------------------------
        # 3. EVENTS BLUEPRINT
        # -------------------------------------------------------------
        print("\n--- [3/5] Testing Events Endpoints (/api/events) ---")

        # 3a. Create event without Admin role -> 403
        event_payload = {
            "title": f"Flask API Workshop {suffix}",
            "description": "Comprehensive tutorial on building production-ready REST APIs with Python Flask and MongoDB Atlas.",
            "category": "Workshop",
            "tags": ["Flask", "API", "PyMongo"],
            "venue": {"type": "in-person", "name": "Computer Lab 3", "address_or_link": "Block C", "city": "Bengaluru"},
            "event_date": (datetime.utcnow() + timedelta(days=10)).isoformat(),
            "duration_hours": 3.0,
            "total_capacity": 20,
            "price": 100.0,
            "organizer_name": "Department of CSE"
        }
        res_ev_unauth = client.post("/api/events", json=event_payload)
        assert res_ev_unauth.status_code == 403  # Regular user session
        print("[PASS] POST /api/events (Forbidden for Regular User) -> 403")

        # 3b. Create event with Admin role (via header/session)
        headers_admin = {"X-User-Id": test_admin_id, "X-User-Role": "admin"}
        res_ev_create = client.post("/api/events", json=event_payload, headers=headers_admin)
        assert res_ev_create.status_code == 201
        test_event_id = res_ev_create.json["event"]["_id"]
        assert res_ev_create.json["event"]["remaining_capacity"] == 20
        print(f"[PASS] POST /api/events (Admin Authorized) -> 201 (Created _id={test_event_id})")

        # 3c. List Events
        res_ev_list = client.get("/api/events?category=Workshop")
        assert res_ev_list.status_code == 200
        assert res_ev_list.json["count"] >= 1
        print(f"[PASS] GET /api/events?category=Workshop -> 200 ({res_ev_list.json['count']} events found)")

        # 3d. Get Single Event
        res_ev_get = client.get(f"/api/events/{test_event_id}")
        assert res_ev_get.status_code == 200
        assert res_ev_get.json["event"]["title"] == event_payload["title"]
        print(f"[PASS] GET /api/events/{test_event_id} -> 200 (Found)")

        # 3e. Text Search Events
        res_ev_search = client.get("/api/events/search?q=Flask")
        assert res_ev_search.status_code == 200
        assert res_ev_search.json["count"] >= 1
        print(f"[PASS] GET /api/events/search?q=Flask -> 200 ({res_ev_search.json['count']} matched)")

        # 3f. Update Event
        res_ev_upd = client.put(
            f"/api/events/{test_event_id}",
            json={"price": 120.0},
            headers=headers_admin
        )
        assert res_ev_upd.status_code == 200
        assert res_ev_upd.json["event"]["price"] == 120.0
        print("[PASS] PUT /api/events/<id> -> 200 (Price Updated)")

        # -------------------------------------------------------------
        # 4. BOOKINGS BLUEPRINT
        # -------------------------------------------------------------
        print("\n--- [4/5] Testing Bookings Endpoints (/api/bookings) ---")

        # 4a. Create Booking (Logged in as student)
        booking_payload = {
            "event_id": test_event_id,
            "tickets_count": 2,
            "attendee_name": f"Student {suffix}",
            "attendee_email": user_email
        }
        res_bk_create = client.post("/api/bookings", json=booking_payload)
        assert res_bk_create.status_code == 201
        test_booking_id = res_bk_create.json["booking"]["_id"]
        booking_code = res_bk_create.json["booking"]["booking_code"]
        assert res_bk_create.json["booking"]["total_amount"] == 2 * 120.0  # 240.0
        print(f"[PASS] POST /api/bookings -> 201 (Booking Confirmed: Code={booking_code}, Amount=₹240)")

        # Verify capacity decremented from 20 to 18
        res_ev_check = client.get(f"/api/events/{test_event_id}")
        assert res_ev_check.json["event"]["remaining_capacity"] == 18
        print("[PASS] Transaction Verified: Remaining capacity atomically decremented to 18")

        # 4b. View My Tickets
        res_my_bk = client.get("/api/bookings/my-tickets")
        assert res_my_bk.status_code == 200
        assert res_my_bk.json["count"] >= 1
        print(f"[PASS] GET /api/bookings/my-tickets -> 200 ({res_my_bk.json['count']} ticket(s) found)")

        # 4c. Lookup Ticket by Booking Code
        res_bk_code = client.get(f"/api/bookings/code/{booking_code}")
        assert res_bk_code.status_code == 200
        assert res_bk_code.json["booking"]["booking_code"] == booking_code
        print(f"[PASS] GET /api/bookings/code/{booking_code} -> 200 (Verified)")

        # 4d. Cancel Booking (Atomic restock)
        res_bk_cancel = client.post(f"/api/bookings/{test_booking_id}/cancel")
        assert res_bk_cancel.status_code == 200
        # Verify capacity restored back to 20
        res_ev_check2 = client.get(f"/api/events/{test_event_id}")
        assert res_ev_check2.json["event"]["remaining_capacity"] == 20
        print("[PASS] POST /api/bookings/<id>/cancel -> 200 (Cancelled and capacity restored to 20)")

        # -------------------------------------------------------------
        # 5. ADMIN & ANALYTICS BLUEPRINT
        # -------------------------------------------------------------
        print("\n--- [5/5] Testing Admin Analytics Endpoints (/api/admin) ---")

        # 5a. Admin endpoints forbidden for regular user
        res_ad_forbidden = client.get("/api/admin/analytics/summary")
        assert res_ad_forbidden.status_code == 403
        print("[PASS] GET /api/admin/analytics/summary (User Forbidden) -> 403")

        # 5b. Platform summary (Admin)
        res_ad_summary = client.get("/api/admin/analytics/summary", headers=headers_admin)
        assert res_ad_summary.status_code == 200
        assert "kpis" in res_ad_summary.json
        print(f"[PASS] GET /api/admin/analytics/summary (Admin) -> 200 (KPIs returned)")

        # 5c. Event Performance Analytics (Admin)
        res_ad_events = client.get("/api/admin/analytics/events", headers=headers_admin)
        assert res_ad_events.status_code == 200
        print(f"[PASS] GET /api/admin/analytics/events (Admin) -> 200 ({res_ad_events.json['count']} events analyzed)")

        # 5d. Category Analytics (Admin)
        res_ad_cats = client.get("/api/admin/analytics/categories", headers=headers_admin)
        assert res_ad_cats.status_code == 200
        print(f"[PASS] GET /api/admin/analytics/categories (Admin) -> 200 ({res_ad_cats.json['count']} categories analyzed)")

        # 5e. Monthly Trends (Admin)
        res_ad_month = client.get("/api/admin/analytics/monthly", headers=headers_admin)
        assert res_ad_month.status_code == 200
        print(f"[PASS] GET /api/admin/analytics/monthly (Admin) -> 200 (Monthly stats returned)")

        # 5f. Admin User & Event Lists
        res_ad_users = client.get("/api/admin/users", headers=headers_admin)
        assert res_ad_users.status_code == 200
        res_ad_all_events = client.get("/api/admin/events", headers=headers_admin)
        assert res_ad_all_events.status_code == 200
        print(f"[PASS] GET /api/admin/users & /api/admin/events -> 200 (Management lists returned)")

        print("\n" + "=" * 65)
        print("ALL FLASK API ROUTES TESTED AND PASSED SUCCESSFULLY!")
        print("=" * 65)
        return True

    finally:
        # Cleanup test documents
        print("\nCleaning up test documents from MongoDB Atlas...")
        if test_booking_id:
            db.bookings.delete_one({"_id": test_booking_id})
        if test_event_id:
            db.events.delete_one({"_id": test_event_id})
        if test_user_id:
            db.users.delete_one({"_id": test_user_id})
        if test_admin_id:
            db.users.delete_one({"_id": test_admin_id})
        print("[OK] Test artifacts cleaned up. Database remains clean.")

if __name__ == "__main__":
    success = run_api_tests()
    sys.exit(0 if success else 1)
