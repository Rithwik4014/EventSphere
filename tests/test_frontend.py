# tests/test_frontend.py
"""
Frontend Verification Suite for EventSphere.
Verifies that all HTML pages, Jinja2 templates, and static assets render with HTTP 200.
"""

import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app

def run_frontend_tests():
    print("=" * 65)
    print("EVENTSPHERE FRONTEND PAGES & ASSETS VERIFICATION")
    print("=" * 65)

    app = create_app("testing")
    client = app.test_client()

    # 1. Test Static Assets
    print("\n--- [1/3] Verifying Static CSS & JavaScript Assets ---")
    static_files = [
        "/static/css/style.css",
        "/static/js/main.js",
        "/static/js/search.js",
        "/static/js/analytics.js"
    ]
    for asset in static_files:
        res = client.get(asset)
        assert res.status_code == 200, f"Asset {asset} failed with {res.status_code}"
        print(f"[PASS] Static Asset: {asset} -> 200 OK ({len(res.data)} bytes)")

    # 2. Test Public & Auth Pages
    print("\n--- [2/3] Verifying Public & Authentication Pages ---")
    public_pages = [
        ("/", "Discover, Book & Experience Events"),
        ("/events", "Events Catalog"),
        ("/login", "Sign In"),
        ("/register", "Create Account"),
        ("/profile", "User Profile"),
        ("/my-bookings", "My Bookings"),
        ("/admin/dashboard", "Admin Analytics Dashboard"),
        ("/admin/manage-events", "Event & User Management"),
        ("/admin/verify", "Ticket Verification"),
        ("/events/create", "Publish New Event")
    ]

    for path, title_fragment in public_pages:
        res = client.get(path)
        assert res.status_code == 200, f"Page {path} failed with {res.status_code}"
        html_content = res.data.decode("utf-8")
        assert "EventSphere" in html_content, f"EventSphere branding missing from {path}"
        print(f"[PASS] Web View: {path} -> 200 OK")

    # 3. Test Detail Page Rendering with Mock ID
    print("\n--- [3/3] Verifying Detail View Route ---")
    res_detail = client.get("/events/654a2001f01a2b3c4d5e0002")
    assert res_detail.status_code == 200
    assert "Reserve Tickets" in res_detail.data.decode("utf-8")
    print("[PASS] Web View: /events/<id> -> 200 OK")

    res_ticket = client.get("/ticket/654a3001f01a2b3c4d5e0003")
    assert res_ticket.status_code == 200
    assert "Digital Ticket" in res_ticket.data.decode("utf-8")
    print("[PASS] Web View: /ticket/<id> -> 200 OK")

    print("\n" + "=" * 65)
    print("ALL FRONTEND PAGES & ASSETS VERIFIED SUCCESSFULLY!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    success = run_frontend_tests()
    sys.exit(0 if success else 1)
