# tests/test_email_and_categories.py
"""
Test Suite for Email Registration Diversity and Expanded Categories.
Verifies:
1. Registration succeeds with popular providers: Gmail, Outlook, Yahoo, and college domains.
2. Email uniqueness and duplicate rejection are strictly maintained.
3. Expanded categories ('Academic', 'Technology', 'Cultural', 'Music & Entertainment',
   'Sports', 'Arts & Creativity', 'Gaming', 'Business & Entrepreneurship', 'Wellness',
   'Social & Community') pass schema validation and service checks.
4. Database contains at least 30 varied sample events across all 10 categories.
5. Category filtering API (/api/events?category=...) returns the expected category events.
6. Clean up temporary test accounts and events afterward.
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
from app.services.event_service import VALID_CATEGORIES

REQUIRED_CATEGORIES = [
    "Technology & Innovation",
    "Education & Learning",
    "Music & Entertainment",
    "Arts & Creativity",
    "Sports & Fitness",
    "Business & Entrepreneurship",
    "Health & Wellness",
    "Food & Lifestyle",
    "Travel & Adventure",
    "Social & Community"
]

def run_tests():
    print("=" * 68)
    print("EVENTSPHERE EMAIL PROVIDERS & EXPANDED CATEGORIES VERIFICATION")
    print("=" * 68)

    app = create_app("testing")
    client = app.test_client()
    db = get_db()
    suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    created_user_ids = []
    created_event_ids = []

    try:
        # -----------------------------------------------------------------
        # 1. EMAIL REGISTRATION WITH DIVERSE DOMAINS
        # -----------------------------------------------------------------
        print("\n--- [1/4] Testing Email Registration Across Diverse Providers ---")
        test_emails = [
            ("Gmail", f"student.{suffix}@gmail.com"),
            ("Outlook", f"developer.{suffix}@outlook.com"),
            ("Yahoo", f"organizer.{suffix}@yahoo.com"),
            ("College Domain", f"scholar.{suffix}@campus.mit.edu"),
            ("Custom Domain", f"innovator.{suffix}@startup.io")
        ]

        for provider, email in test_emails:
            payload = {
                "name": f"Test User {provider}",
                "email": email,
                "password": "Password123!",
                "preferences": {
                    "favorite_categories": ["Technology", "Wellness"],
                    "receive_notifications": True
                }
            }
            res = client.post("/api/auth/register", json=payload)
            assert res.status_code == 201, f"Failed to register with {provider} email ({email}): {res.data}"
            user_data = res.json["user"]
            created_user_ids.append(user_data["_id"])
            assert user_data["email"] == email.lower()
            assert user_data["role"] == "user"
            print(f" [PASS] Successfully registered account with {provider} ({email})")

        # -----------------------------------------------------------------
        # 2. EMAIL UNIQUENESS & DUPLICATE REJECTION
        # -----------------------------------------------------------------
        print("\n--- [2/4] Testing Email Uniqueness & Duplicate Protection ---")
        primary_gmail = f"student.{suffix}@gmail.com"
        dup_payload = {
            "name": "Duplicate Attempter",
            "email": primary_gmail.upper(),  # Test case-insensitivity
            "password": "Password123!"
        }
        res_dup = client.post("/api/auth/register", json=dup_payload)
        assert res_dup.status_code == 400, "Duplicate email registration should be rejected with 400"
        assert "already exists" in res_dup.json.get("error", "").lower()
        print(f" [PASS] Duplicate email registration ({primary_gmail.upper()}) was correctly rejected.")

        # -----------------------------------------------------------------
        # 3. VERIFY SAMPLE EVENTS DISTRIBUTION ACROSS 10 CATEGORIES
        # -----------------------------------------------------------------
        print("\n--- [3/4] Verifying Seeded Sample Events in MongoDB Atlas ---")
        total_events_count = db.events.count_documents({})
        print(f" Total events in database: {total_events_count}")
        assert total_events_count >= 30, f"Expected at least 30 events, found {total_events_count}"

        category_counts = {}
        for cat in REQUIRED_CATEGORIES:
            count = db.events.count_documents({"category": cat})
            category_counts[cat] = count
            print(f"  - Category '{cat}': {count} events")
            assert count >= 1, f"Category '{cat}' has no events in database!"

        print(f" [PASS] All 10 required categories are actively represented in database.")

        # -----------------------------------------------------------------
        # 4. CATEGORY FILTERING & EVENT CREATION API
        # -----------------------------------------------------------------
        print("\n--- [4/4] Testing Category Filtering & API Validation ---")
        import urllib.parse
        for cat in REQUIRED_CATEGORIES:
            encoded_cat = urllib.parse.quote(cat)
            res_cat = client.get(f"/api/events?category={encoded_cat}")
            assert res_cat.status_code == 200
            data = res_cat.json
            assert data["success"] is True
            assert data["count"] >= 1, f"Expected events for category '{cat}', got 0"
            for ev in data["events"]:
                assert ev["category"] == cat
            print(f" [PASS] Filter GET /api/events?category={encoded_cat} -> {data['count']} events verified")

        # Test creating an event with a new category
        # First log in with existing admin account
        admin_login = client.post("/api/auth/login", json={"email": "admin@edusphere.in", "password": "admin123"})
        assert admin_login.status_code == 200, "Admin login failed"
        admin_id = admin_login.json["user"]["_id"]

        test_new_cat_event = {
            "title": f"Test Wellness Retreat {suffix}",
            "description": "Mindfulness, guided meditation, and yoga sessions for holistic health and wellness.",
            "category": "Health & Wellness",
            "tags": ["Wellness", "Health", "Meditation"],
            "venue": {
                "type": "in-person",
                "name": "Zen Pavilion",
                "address_or_link": "Metropolitan Green Promenade",
                "city": "Bengaluru"
            },
            "event_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
            "duration_hours": 2.0,
            "total_capacity": 50,
            "price": 0.0,
            "organizer_name": "EventSphere Global Events"
        }
        res_create = client.post(
            "/api/events",
            json=test_new_cat_event
        )
        assert res_create.status_code == 201, f"Create event failed: {res_create.data}"
        new_event = res_create.json["event"]
        created_event_ids.append(new_event["_id"])
        assert new_event["category"] == "Health & Wellness"
        print(f" [PASS] Successfully published new event under category 'Health & Wellness' (_id={new_event['_id']})")

        print("\n" + "=" * 68)
        print("ALL EMAIL & EXPANDED CATEGORY TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 68)
        return True

    finally:
        print("\nCleaning up test accounts and test events...")
        if created_user_ids:
            from bson import ObjectId
            oids = [ObjectId(uid) if isinstance(uid, str) else uid for uid in created_user_ids]
            res_del_u = db.users.delete_many({"_id": {"$in": oids}})
            print(f" Removed {res_del_u.deleted_count} temporary test users.")
        if created_event_ids:
            from bson import ObjectId
            oids = [ObjectId(eid) if isinstance(eid, str) else eid for eid in created_event_ids]
            res_del_e = db.events.delete_many({"_id": {"$in": oids}})
            print(f" Removed {res_del_e.deleted_count} temporary test events.")
        print("[OK] Cleanup completed.")

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
