# tests/test_security_rbac.py
"""
Security & Role-Based Access Control (RBAC) Verification Suite for EventSphere.
Verifies:
1. Public registration (POST /api/auth/register) strictly forces role="user",
   even when the client payload explicitly requests role="admin".
2. Users cannot escalate privileges or change their role via PUT /api/auth/profile.
3. Unauthenticated requests to PUT /api/admin/users/<id>/role are rejected (401).
4. Regular user requests to PUT /api/admin/users/<id>/role are forbidden (403).
5. Only an existing authenticated admin can promote a user to admin (200).
6. Demo admin login succeeds with existing admin credentials.
"""

import os
import sys
from datetime import datetime

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from app.services.db import get_db
from app.services.user_service import UserService

def run_security_tests():
    print("=" * 65)
    print("EVENTSPHERE SECURITY & RBAC PRIVILEGE TEST SUITE")
    print("=" * 65)

    app = create_app("testing")
    client = app.test_client()
    db = get_db()
    suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    attacker_email = f"attacker.{suffix}@college.edu"
    target_user_email = f"target.student.{suffix}@college.edu"

    created_user_ids = []

    try:
        # -------------------------------------------------------------
        # TEST 1: Privilege Escalation via Registration
        # -------------------------------------------------------------
        print("\n--- [Test 1] Public Registration Exploitation Prevention ---")
        malicious_payload = {
            "name": f"Malicious Actor {suffix}",
            "email": attacker_email,
            "password": "Password123!",
            "role": "admin"  # Explicitly attempting to register as admin
        }

        res_reg = client.post("/api/auth/register", json=malicious_payload)
        assert res_reg.status_code == 201
        created_user = res_reg.json["user"]
        created_user_ids.append(created_user["_id"])

        # Check in DB directly
        db_user = db.users.find_one({"email": attacker_email})
        assert db_user is not None
        assert db_user["role"] == "user", f"VULNERABILITY DETECTED: User received role '{db_user['role']}'!"
        assert created_user["role"] == "user"
        print(f"[PASS] Public registration with explicit role='admin' was forced to role='user'.")
        print(f"       Database verified role: '{db_user['role']}' (User ID: {db_user['_id']})")

        # -------------------------------------------------------------
        # TEST 2: Privilege Escalation via Profile Update
        # -------------------------------------------------------------
        print("\n--- [Test 2] Profile Update Role Tampering Prevention ---")
        # Log in as the attacker
        login_res = client.post("/api/auth/login", json={
            "email": attacker_email,
            "password": "Password123!"
        })
        assert login_res.status_code == 200

        # Attempt to escalate role to admin via profile update
        res_tamper = client.put("/api/auth/profile", json={
            "name": "Attacker Renamed",
            "role": "admin"
        })
        assert res_tamper.status_code == 200

        # Verify DB still has role='user'
        db_user_after = db.users.find_one({"email": attacker_email})
        assert db_user_after["role"] == "user", "VULNERABILITY: User escalated role via profile update!"
        print(f"[PASS] Attempted PUT /api/auth/profile with role='admin' was ignored.")
        print(f"       Database verified role remains: '{db_user_after['role']}'")

        # -------------------------------------------------------------
        # TEST 3: Unauthenticated Access to Role Promotion Endpoint
        # -------------------------------------------------------------
        print("\n--- [Test 3] Unauthenticated Promotion Endpoint Rejection ---")
        # Clear session
        client.get("/api/auth/logout")

        # Register a target innocent user
        target_res = client.post("/api/auth/register", json={
            "name": "Target Student",
            "email": target_user_email,
            "password": "TargetPass123!"
        })
        target_id = target_res.json["user"]["_id"]
        created_user_ids.append(target_id)

        res_unauth = client.put(f"/api/admin/users/{target_id}/role", json={"role": "admin"})
        assert res_unauth.status_code == 401
        print("[PASS] Unauthenticated PUT /api/admin/users/<id>/role rejected with 401 Unauthorized.")

        # -------------------------------------------------------------
        # TEST 4: Unauthorized User Attempting to Promote
        # -------------------------------------------------------------
        print("\n--- [Test 4] Regular User Forbidden from Promoting Users ---")
        # Log back in as attacker (regular user)
        client.post("/api/auth/login", json={"email": attacker_email, "password": "Password123!"})

        res_forbidden = client.put(f"/api/admin/users/{target_id}/role", json={"role": "admin"})
        assert res_forbidden.status_code == 403
        print("[PASS] Regular user cannot promote users: rejected with 403 Forbidden.")

        # Self-promotion attempt
        res_self_promo = client.put(f"/api/admin/users/{created_user['_id']}/role", json={"role": "admin"})
        assert res_self_promo.status_code == 403
        print("[PASS] Regular user self-promotion blocked with 403 Forbidden.")

        # -------------------------------------------------------------
        # TEST 5: Legitimate Admin Promotion
        # -------------------------------------------------------------
        print("\n--- [Test 5] Legitimate Admin Promotion via Admin Endpoint ---")
        # Log in as demo admin
        admin_login = client.post("/api/auth/login", json={
            "email": "admin@edusphere.in",
            "password": "admin123"
        })
        assert admin_login.status_code == 200, "Demo admin account should exist and authenticate."

        # Admin promotes target user
        res_promote = client.put(f"/api/admin/users/{target_id}/role", json={"role": "admin"})
        assert res_promote.status_code == 200
        assert res_promote.json["user"]["role"] == "admin"

        # Verify DB reflects promotion
        db_target = db.users.find_one({"email": target_user_email})
        assert db_target["role"] == "admin"
        print(f"[PASS] Authenticated admin successfully promoted target user.")
        print(f"       Database verified updated role: '{db_target['role']}'")

        # -------------------------------------------------------------
        # TEST 6: Demo Accounts Functionality Check
        # -------------------------------------------------------------
        print("\n--- [Test 6] Preserved Demo Accounts Authentication ---")
        res_stu = client.post("/api/auth/login", json={"email": "rithwik@edusphere.in", "password": "rithwik123"})
        assert res_stu.status_code == 200
        assert res_stu.json["user"]["role"] == "user"

        res_adm = client.post("/api/auth/login", json={"email": "admin@edusphere.in", "password": "admin123"})
        assert res_adm.status_code == 200
        assert res_adm.json["user"]["role"] == "admin"
        print("[PASS] Both rithwik@edusphere.in and admin@edusphere.in authenticate successfully with intended roles.")

        print("\n" + "=" * 65)
        print("ALL SECURITY & RBAC TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 65)
        return True

    finally:
        # Cleanup test users (preserve seeded demo accounts)
        print("\nCleaning up test accounts...")
        if created_user_ids:
            from bson import ObjectId
            oids = [ObjectId(uid) if isinstance(uid, str) else uid for uid in created_user_ids]
            db.users.delete_many({"_id": {"$in": oids}})
        print("[OK] Test accounts cleaned up.")

if __name__ == "__main__":
    success = run_security_tests()
    sys.exit(0 if success else 1)
