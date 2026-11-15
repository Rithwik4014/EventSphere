# scripts/seed_demo_accounts.py
"""
Seeds the primary demo accounts (admin and sample user) for local development
and testing. Enforces strict production guards to prevent predictable credentials.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from werkzeug.security import generate_password_hash
from app.services.db import get_db
from app.services.user_service import UserService

def seed_demo_accounts():
    db = get_db()
    flask_env = os.environ.get("FLASK_ENV", "development").lower()
    is_production = flask_env in ("production", "prod")

    print(f"Checking accounts in MongoDB Atlas (Environment: {flask_env})...")
    result = {
        "is_production": is_production,
        "admin_status": None,
        "user_status": None
    }

    # 1. Admin Account Configuration
    admin_email = os.environ.get("INITIAL_ADMIN_EMAIL") or os.environ.get("ADMIN_EMAIL") or "admin@edusphere.in"
    admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD")

    # Production Guard: Prohibit default/predictable admin passwords in production
    if is_production:
        if not admin_password:
            print("[SECURITY WARNING] Running in production mode (FLASK_ENV=production).")
            print("  - To create an initial administrator, provide INITIAL_ADMIN_PASSWORD in environment variables.")
            print("  - Default password ('admin123') is strictly disallowed in production.")
        elif admin_password == "admin123":
            raise ValueError("Refusing to seed admin: 'admin123' is a prohibited default password in production.")
    else:
        # Development / Testing fallback
        if not admin_password:
            admin_password = "admin123"

    existing_admin = UserService.get_user_by_email(admin_email)
    if not existing_admin:
        if admin_password:
            hashed_admin_pwd = generate_password_hash(admin_password)
            admin_doc = UserService.create_user(
                name="System Administrator",
                email=admin_email,
                password_hash=hashed_admin_pwd,
                role="admin",
                preferences={"favorite_categories": ["Technology & Innovation"], "receive_notifications": True}
            )
            print(f"[OK] Created initial admin account: {admin_email} (role: admin, _id: {admin_doc['_id']})")
            result["admin_status"] = "created"
        else:
            print(f"[SKIP] No existing admin found and no secure INITIAL_ADMIN_PASSWORD provided for production.")
            result["admin_status"] = "skipped_no_password"
    else:
        # SECURITY FIX: Never overwrite an existing administrator's password in production or development!
        if existing_admin.get("role") != "admin":
            UserService.update_user(existing_admin["_id"], {"role": "admin"})
            print(f"[OK] Updated existing account {admin_email} role to 'admin'. Password hash preserved.")
            result["admin_status"] = "updated_role_only"
        else:
            print(f"[EXISTS] Admin account {admin_email} already exists. Existing password preserved.")
            result["admin_status"] = "preserved"

    # 2. Sample User Account (for local development/evaluation)
    allow_sample_user = not is_production or os.environ.get("SEED_DEMO_ACCOUNTS", "false").lower() in ("true", "1", "yes")
    if allow_sample_user:
        user_email = os.environ.get("SAMPLE_USER_EMAIL", "user@edusphere.in")
        user_password = os.environ.get("SAMPLE_USER_PASSWORD", "user123")
        existing_user = UserService.get_user_by_email(user_email)
        if not existing_user:
            hashed_user_pwd = generate_password_hash(user_password)
            user_doc = UserService.create_user(
                name="Sample User",
                email=user_email,
                password_hash=hashed_user_pwd,
                role="user",
                preferences={"favorite_categories": ["Technology & Innovation", "Music & Entertainment"], "receive_notifications": True}
            )
            print(f"[OK] Created initial sample user account: {user_email} (role: user, _id: {user_doc['_id']})")
            result["user_status"] = "created"
        else:
            if existing_user.get("role") != "user":
                UserService.update_user(existing_user["_id"], {"role": "user"})
            print(f"[EXISTS] Sample user account {user_email} is active. Existing password preserved.")
            result["user_status"] = "preserved"
    else:
        print("[SKIP] Skipping sample user creation in production environment (set SEED_DEMO_ACCOUNTS=true to enable).")
        result["user_status"] = "skipped_production"

    # Clean up deprecated student demo account if present
    old_student = UserService.get_user_by_email("rithwik@edusphere.in")
    if old_student:
        db.users.delete_one({"_id": old_student["_id"]})
        print("[CLEANUP] Removed old student demo account rithwik@edusphere.in.")

    print("Accounts verification complete.")
    return result

if __name__ == "__main__":
    try:
        seed_demo_accounts()
    except ValueError as e:
        print(f"[SECURITY ERROR] {e}")
        sys.exit(1)
