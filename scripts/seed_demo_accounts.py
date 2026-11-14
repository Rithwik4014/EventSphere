# scripts/seed_demo_accounts.py
"""
Seeds the primary demo accounts (admin and student) if they do not already exist.
Preserves existing records without modification.
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
    print("Checking demo accounts in MongoDB Atlas...")

    # 1. Admin Demo Account
    admin_email = "admin@edusphere.in"
    existing_admin = UserService.get_user_by_email(admin_email)
    if not existing_admin:
        hashed_admin_pwd = generate_password_hash("admin123")
        admin_doc = UserService.create_user(
            name="System Administrator",
            email=admin_email,
            password_hash=hashed_admin_pwd,
            role="admin",
            preferences={"favorite_categories": ["Technology & Innovation"], "receive_notifications": True}
        )
        print(f"[OK] Created initial admin account: {admin_email} (role: admin, _id: {admin_doc['_id']})")
    else:
        # Ensure it has admin role and updated password
        hashed_admin_pwd = generate_password_hash("admin123")
        UserService.update_user(existing_admin["_id"], {"role": "admin", "password_hash": hashed_admin_pwd})
        print(f"[EXISTS] Admin account {admin_email} is active and updated.")

    # 2. Student Demo Account
    student_email = "rithwik@edusphere.in"
    existing_student = UserService.get_user_by_email(student_email)
    if not existing_student:
        hashed_student_pwd = generate_password_hash("rithwik123")
        student_doc = UserService.create_user(
            name="Rithwik",
            email=student_email,
            password_hash=hashed_student_pwd,
            role="user",
            preferences={"favorite_categories": ["Technology & Innovation", "Music & Entertainment"], "receive_notifications": True}
        )
        print(f"[OK] Created initial student account: {student_email} (role: user, _id: {student_doc['_id']})")
    else:
        hashed_student_pwd = generate_password_hash("rithwik123")
        UserService.update_user(existing_student["_id"], {"role": "user", "password_hash": hashed_student_pwd})
        print(f"[EXISTS] Student account {student_email} is active and updated.")

    print("Demo accounts seeding complete.")

if __name__ == "__main__":
    seed_demo_accounts()
