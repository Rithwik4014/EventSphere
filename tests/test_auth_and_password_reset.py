# tests/test_auth_and_password_reset.py
"""
Comprehensive Test Suite for EventSphere Authentication & Password Reset:
1. Sample user login (user@edusphere.in / user123).
2. Admin login (admin@edusphere.in / admin123).
3. Sample User Quick Fill verification on login page.
4. Invalid login attempt rejection.
5. Password reset workflow:
   - Email delivery unconfigured notice.
   - SHA-256 token hashing (no plaintext tokens stored).
   - Successful password reset with valid token.
   - Token reuse prevention (single-use enforcement).
   - Token expiration enforcement.
   - Invalid token rejection.
6. RBAC & public registration safety (cannot register as admin).
"""

import os
import sys
import hashlib
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from app.services.db import get_db
from app.services.user_service import UserService

def run_tests():
    print("=" * 70)
    print("EVENTSPHERE AUTHENTICATION & PASSWORD RESET TEST SUITE")
    print("=" * 70)

    app = create_app("testing")
    client = app.test_client()
    db = get_db()

    with app.app_context():
        # -------------------------------------------------------------
        # TEST 1: Sample User Login with Updated Credentials
        # -------------------------------------------------------------
        print("\n--- [Test 1] Verifying Sample User Login (user@edusphere.in) ---")
        res_stu = client.post("/api/auth/login", json={
            "email": "user@edusphere.in",
            "password": "user123"
        })
        assert res_stu.status_code == 200, f"Sample user login failed: {res_stu.data}"
        stu_data = res_stu.json
        assert stu_data["success"] is True
        assert stu_data["user"]["role"] == "user"
        assert stu_data["user"]["email"] == "user@edusphere.in"
        print(f"[PASS] Sample user user@edusphere.in logged in successfully (Role: {stu_data['user']['role']}).")

        # -------------------------------------------------------------
        # TEST 2: Admin Login with Preserved Credentials
        # -------------------------------------------------------------
        print("\n--- [Test 2] Verifying Admin Login (admin@edusphere.in) ---")
        res_adm = client.post("/api/auth/login", json={
            "email": "admin@edusphere.in",
            "password": "admin123"
        })
        assert res_adm.status_code == 200, f"Admin login failed: {res_adm.data}"
        adm_data = res_adm.json
        assert adm_data["success"] is True
        assert adm_data["user"]["role"] == "admin"
        assert adm_data["user"]["email"] == "admin@edusphere.in"
        print(f"[PASS] Admin admin@edusphere.in logged in successfully (Role: {adm_data['user']['role']}).")

        # -------------------------------------------------------------
        # TEST 3: Login Page & Sample User Quick-Fill UI Verification
        # -------------------------------------------------------------
        print("\n--- [Test 3] Verifying Login Page & Quick Fill Elements ---")
        res_login_page = client.get("/login")
        assert res_login_page.status_code == 200
        html = res_login_page.data.decode("utf-8")

        # Must have "Sample User" button and fillSampleUser() JS function
        assert "Sample User" in html, "'Sample User' button missing from login.html"
        assert "fillSampleUser()" in html, "'fillSampleUser()' JS function missing"
        assert "user@edusphere.in" in html, "user@edusphere.in missing from JS function"
        assert "user123" in html, "user123 missing from JS function"

        # Visible text verification: ensure credentials and duplicate heading are not rendered in markup
        markup_before_script = html.split("<script>")[0]
        assert "user123" not in markup_before_script, "Security issue: Password 'user123' exposed as visible text in HTML"
        assert "Password:" not in markup_before_script, "Credential label 'Password:' found in HTML"
        assert "Email: user@edusphere.in" not in markup_before_script, "Email credential text found in HTML"

        # Must NOT have old student demo credentials
        assert "Fill Student" not in html, "Old 'Fill Student' button still present in login.html"
        assert "rithwik@edusphere.in" not in html, "Old student email rithwik@edusphere.in found in login.html"
        assert "rithwik123" not in html, "Old student password rithwik123 found in login.html"

        # Must NOT have admin credentials exposed
        assert "Fill Admin" not in html, "Security issue: 'Fill Admin' button found in login.html"
        assert "admin@edusphere.in" not in html, "Admin credentials exposed in client login template"
        assert "admin123" not in html, "Admin password exposed in client login template"

        # Must NOT have Forgot Password link
        assert "Forgot Password?" not in html, "'Forgot Password?' link should be completely removed from login.html"
        assert "/forgot-password" not in html, "Link to /forgot-password should be completely removed from login.html"
        print("[PASS] Login page correctly displays single 'Sample User' button without visible password text.")
        print("[PASS] 'Forgot Password?' link is completely absent from the login page.")

        # -------------------------------------------------------------
        # TEST 4: Invalid Login Attempts
        # -------------------------------------------------------------
        print("\n--- [Test 4] Verifying Invalid Login Rejection ---")
        # Wrong password
        res_bad_pw = client.post("/api/auth/login", json={
            "email": "user@edusphere.in",
            "password": "wrongPassword123!"
        })
        assert res_bad_pw.status_code == 401
        assert res_bad_pw.json["success"] is False

        # Non-existent email
        res_bad_email = client.post("/api/auth/login", json={
            "email": "nonexistent.user.2026@edusphere.in",
            "password": "somePassword123!"
        })
        assert res_bad_email.status_code == 401
        assert res_bad_email.json["success"] is False

        # Missing email or password
        res_missing = client.post("/api/auth/login", json={"email": "user@edusphere.in"})
        assert res_missing.status_code == 400
        print("[PASS] Invalid login attempts (wrong password, non-existent email, missing fields) rejected correctly.")

        # -------------------------------------------------------------
        # TEST 5: Password Recovery Request when Email Unconfigured
        # -------------------------------------------------------------
        print("\n--- [Test 5] Password Recovery Request & Email Unconfigured Notice ---")
        res_forgot = client.post("/api/auth/forgot-password", json={
            "email": "user@edusphere.in"
        })
        assert res_forgot.status_code == 503
        data_forgot = res_forgot.json
        assert data_forgot["success"] is False
        assert data_forgot["email_configured"] is False
        assert "SMTP configuration" in data_forgot["error"] or "email" in data_forgot["error"]
        print("[PASS] System clearly indicates password recovery requires SMTP email configuration rather than pretending an email was sent.")

        # -------------------------------------------------------------
        # TEST 6: Secure Password Reset Token Workflow & Hash Storage
        # -------------------------------------------------------------
        print("\n--- [Test 6] Secure Token Generation, SHA-256 Hashing, & Verification ---")
        raw_token = UserService.create_password_reset_token("user@edusphere.in", expires_in_minutes=15)
        assert raw_token and len(raw_token) >= 32

        # Check DB record: raw_token MUST NOT be in DB; only token_hash (SHA-256)
        expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        stored_record = db.password_resets.find_one({"token_hash": expected_hash})
        assert stored_record is not None, "Password reset document not found in database"
        assert stored_record.get("raw_token") is None, "Security violation: raw token stored in DB!"
        assert stored_record["token_hash"] == expected_hash
        assert stored_record["used"] is False
        assert stored_record["expires_at"] > datetime.utcnow()
        print("[PASS] Reset token is cryptographically secure and stored only as SHA-256 hash (never plaintext).")

        # Execute password reset with valid token
        new_test_pw = "newUserPass2026!"
        res_reset = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": new_test_pw
        })
        assert res_reset.status_code == 200, f"Reset password failed: {res_reset.data}"
        assert res_reset.json["success"] is True

        # Verify old password no longer works
        old_login = client.post("/api/auth/login", json={
            "email": "user@edusphere.in",
            "password": "user123"
        })
        assert old_login.status_code == 401, "Old password must not work after reset!"

        # Verify new password works
        new_login = client.post("/api/auth/login", json={
            "email": "user@edusphere.in",
            "password": new_test_pw
        })
        assert new_login.status_code == 200, "New password must authenticate successfully!"
        print("[PASS] Password successfully reset. Old password invalidated; new password authenticated.")

        # -------------------------------------------------------------
        # TEST 7: Single-Use Enforcement (Reuse Prevention)
        # -------------------------------------------------------------
        print("\n--- [Test 7] Verifying Single-Use Enforcement (Token Reuse Prevention) ---")
        res_reuse = client.post("/api/auth/reset-password", json={
            "token": raw_token,
            "new_password": "AnotherPassword123!"
        })
        assert res_reuse.status_code == 400, "Reused token must be rejected!"
        assert "already been used" in res_reuse.json["error"]
        print(f"[PASS] Token reuse rejected with 400: '{res_reuse.json['error']}'")

        # -------------------------------------------------------------
        # TEST 8: Token Expiration Enforcement
        # -------------------------------------------------------------
        print("\n--- [Test 8] Verifying Token Expiration Enforcement ---")
        # Create expired token (expires_in_minutes=-10)
        expired_token = UserService.create_password_reset_token("user@edusphere.in", expires_in_minutes=-10)
        res_expired = client.post("/api/auth/reset-password", json={
            "token": expired_token,
            "new_password": "YetAnotherPassword123!"
        })
        assert res_expired.status_code == 400, "Expired token must be rejected!"
        assert "expired" in res_expired.json["error"]
        print(f"[PASS] Expired token rejected with 400: '{res_expired.json['error']}'")

        # -------------------------------------------------------------
        # TEST 9: Invalid / Tampered Token Rejection
        # -------------------------------------------------------------
        print("\n--- [Test 9] Verifying Tampered/Fake Token Rejection ---")
        res_fake = client.post("/api/auth/reset-password", json={
            "token": "fake_non_existent_token_1234567890",
            "new_password": "YetAnotherPassword123!"
        })
        assert res_fake.status_code == 400
        assert "Invalid" in res_fake.json["error"] or "unrecognized" in res_fake.json["error"]
        print(f"[PASS] Fake token rejected with 400: '{res_fake.json['error']}'")

        # Restore original user123 password
        from werkzeug.security import generate_password_hash
        user_doc = UserService.get_user_by_email("user@edusphere.in")
        UserService.update_user(user_doc["_id"], {"password_hash": generate_password_hash("user123")})
        print("[OK] Restored user@edusphere.in password to 'user123'.")

        # -------------------------------------------------------------
        # TEST 10: Public Registration Security (Cannot register as admin)
        # -------------------------------------------------------------
        print("\n--- [Test 10] Verifying Public Registration Role Protection ---")
        suffix = int(datetime.utcnow().timestamp())
        res_reg = client.post("/api/auth/register", json={
            "name": f"Hacker Attempt {suffix}",
            "email": f"hacker.{suffix}@example.com",
            "password": "Password123!",
            "role": "admin"  # malicious role attempt
        })
        assert res_reg.status_code == 201
        hacker_user = res_reg.json["user"]
        assert hacker_user["role"] == "user", "CRITICAL SECURITY FLAW: Public registration accepted role='admin'!"
        # Clean up
        db.users.delete_one({"_id": hacker_user["_id"]})
        print("[PASS] Public registration strictly assigns role='user' regardless of request payload.")

        print("\n" + "=" * 70)
        print("ALL AUTHENTICATION & PASSWORD RESET TESTS PASSED WITH 100% SUCCESS!")
        print("=" * 70)

if __name__ == "__main__":
    run_tests()
