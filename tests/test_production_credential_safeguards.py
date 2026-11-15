# tests/test_production_credential_safeguards.py
"""
Test Suite for Production Credential Safeguards and Password Preservation.

Verifies:
1. Production mode strictly rejects default admin credentials ('admin123').
2. Production mode requires secure environment variables for initial admin creation.
3. Production mode skips sample attendee creation by default (SEED_DEMO_ACCOUNTS=false).
4. Existing administrator password hashes are NEVER overwritten.
5. Local development mode continues to support local evaluation credentials.
"""

import os
import sys
import unittest
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import create_app
from app.services.db import get_db, to_object_id
from app.services.user_service import UserService
from scripts.seed_demo_accounts import seed_demo_accounts

def run_credential_safeguard_tests():
    app = create_app()
    with app.app_context():
        db = get_db()
        print("=" * 80)
        print("EVENTSPHERE PRODUCTION CREDENTIAL SAFEGUARDS & PASSWORD PRESERVATION TESTS")
        print("=" * 80)

        original_flask_env = os.environ.get("FLASK_ENV")
        original_admin_pwd = os.environ.get("INITIAL_ADMIN_PASSWORD")
        original_admin_email = os.environ.get("INITIAL_ADMIN_EMAIL")
        original_seed_flag = os.environ.get("SEED_DEMO_ACCOUNTS")

        try:
            # ---------------------------------------------------------
            # TEST 1: Production Guard - Strict Rejection of 'admin123'
            # ---------------------------------------------------------
            print("\n--- [Test 1] Production Mode Strictly Rejects Default 'admin123' ---")
            os.environ["FLASK_ENV"] = "production"
            os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"

            rejected = False
            try:
                seed_demo_accounts()
            except ValueError as e:
                rejected = True
                assert "prohibited default password in production" in str(e)
                print(f"[PASS] seed_demo_accounts strictly raised ValueError: '{e}'")

            assert rejected, "Production guard failed to reject default 'admin123' password!"

            # ---------------------------------------------------------
            # TEST 2: Production Guard - Missing Password Skips Creation
            # ---------------------------------------------------------
            print("\n--- [Test 2] Production Mode Without Password Skips Insecure Admin Seeding ---")
            os.environ["FLASK_ENV"] = "production"
            os.environ.pop("INITIAL_ADMIN_PASSWORD", None)
            os.environ["INITIAL_ADMIN_EMAIL"] = f"prod.admin.{ObjectId()}@enterprise.org"

            res_prod = seed_demo_accounts()
            assert res_prod["is_production"] is True
            assert res_prod["admin_status"] == "skipped_no_password"

            # Verify no account was created with this email
            prod_user = db.users.find_one({"email": os.environ["INITIAL_ADMIN_EMAIL"]})
            assert prod_user is None, "Insecure admin account should not have been created!"
            print("[PASS] Production mode safely skipped admin creation when no INITIAL_ADMIN_PASSWORD was set.")

            # ---------------------------------------------------------
            # TEST 3: Production Guard - Sample Attendee Skipped by Default
            # ---------------------------------------------------------
            print("\n--- [Test 3] Production Mode Skips Sample Attendee by Default ---")
            os.environ["FLASK_ENV"] = "production"
            os.environ["SEED_DEMO_ACCOUNTS"] = "false"

            res_sample_skip = seed_demo_accounts()
            assert res_sample_skip["user_status"] == "skipped_production"
            print("[PASS] Sample attendee creation was skipped in production environment.")

            # ---------------------------------------------------------
            # TEST 4: Password Preservation - Never Overwrite Existing Admin Hash
            # ---------------------------------------------------------
            print("\n--- [Test 4] Preserving Existing Administrator Password Hash ---")
            # Create a test admin with a custom secure password
            test_admin_email = f"secure.admin.{ObjectId()}@enterprise.org"
            custom_password = "SuperSecureCustomAdminPassword2026!#"
            custom_hash = generate_password_hash(custom_password)

            created_admin = UserService.create_user(
                name="Existing Production Admin",
                email=test_admin_email,
                password_hash=custom_hash,
                role="admin",
                preferences={"favorite_categories": ["Technology & Innovation"]}
            )
            created_admin_id = created_admin["_id"]

            # Run seed_demo_accounts targeting this admin email with development fallback
            os.environ["FLASK_ENV"] = "development"
            os.environ["INITIAL_ADMIN_EMAIL"] = test_admin_email
            os.environ.pop("INITIAL_ADMIN_PASSWORD", None)

            res_dev_run = seed_demo_accounts()
            assert res_dev_run["admin_status"] == "preserved"

            # Verify in MongoDB that the stored password hash remains the custom hash
            admin_after_run = db.users.find_one({"_id": created_admin_id})
            assert admin_after_run["password_hash"] == custom_hash, "CRITICAL: Existing admin password hash was overwritten!"
            assert check_password_hash(admin_after_run["password_hash"], custom_password), "Custom password no longer verifies!"
            assert not check_password_hash(admin_after_run["password_hash"], "admin123"), "Admin password was reverted to 'admin123'!"
            print("[PASS] Existing admin password hash was 100% preserved and never overwritten.")

            # Clean up test admin
            db.users.delete_one({"_id": created_admin_id})
            print("[OK] Test admin cleaned up.")

            # ---------------------------------------------------------
            # TEST 5: Local Development Mode Preserves Local Evaluation Accounts
            # ---------------------------------------------------------
            print("\n--- [Test 5] Local Development Mode Preserves Demo Evaluation Accounts ---")
            os.environ["FLASK_ENV"] = "development"
            os.environ.pop("INITIAL_ADMIN_EMAIL", None)
            os.environ.pop("INITIAL_ADMIN_PASSWORD", None)
            os.environ["SEED_DEMO_ACCOUNTS"] = "true"

            res_local = seed_demo_accounts()
            assert res_local["is_production"] is False

            # Verify local evaluation accounts exist and authenticate
            admin_doc = UserService.get_user_by_email("admin@edusphere.in")
            user_doc = UserService.get_user_by_email("user@edusphere.in")
            assert admin_doc is not None, "Local admin account must exist in development!"
            assert user_doc is not None, "Local sample user account must exist in development!"
            assert check_password_hash(admin_doc["password_hash"], "admin123")
            assert check_password_hash(user_doc["password_hash"], "user123")
            print("[PASS] Local development demo functionality preserved for admin@edusphere.in and user@edusphere.in.")

            print("\n" + "=" * 80)
            print("ALL PRODUCTION CREDENTIAL SAFEGUARD TESTS PASSED WITH 100% SUCCESS!")
            print("=" * 80)

        finally:
            # Restore environment variables
            if original_flask_env is not None:
                os.environ["FLASK_ENV"] = original_flask_env
            else:
                os.environ.pop("FLASK_ENV", None)

            if original_admin_pwd is not None:
                os.environ["INITIAL_ADMIN_PASSWORD"] = original_admin_pwd
            else:
                os.environ.pop("INITIAL_ADMIN_PASSWORD", None)

            if original_admin_email is not None:
                os.environ["INITIAL_ADMIN_EMAIL"] = original_admin_email
            else:
                os.environ.pop("INITIAL_ADMIN_EMAIL", None)

            if original_seed_flag is not None:
                os.environ["SEED_DEMO_ACCOUNTS"] = original_seed_flag
            else:
                os.environ.pop("SEED_DEMO_ACCOUNTS", None)

if __name__ == "__main__":
    run_credential_safeguard_tests()
