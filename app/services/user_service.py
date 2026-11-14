# app/services/user_service.py
"""
User Service for EventSphere.
Implements CRUD operations with PyMongo, handling ObjectId conversions,
duplicate key errors, and schema validation failures.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from pymongo.errors import DuplicateKeyError, OperationFailure
from werkzeug.security import generate_password_hash
from .db import get_db, to_object_id

class UserService:
    @staticmethod
    def get_collection():
        return get_db().users

    @staticmethod
    def get_resets_collection():
        return get_db().password_resets

    @classmethod
    def create_user(cls, name, email, password_hash, role="user", preferences=None):
        """
        Create a new user document.
        Handles duplicate email and schema validation failures.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Name is required and must be a string.")
        if not email or not isinstance(email, str):
            raise ValueError("Valid email address is required.")
        if not password_hash or not isinstance(password_hash, str):
            raise ValueError("Password hash is required.")

        normalized_email = email.strip().lower()
        now = datetime.utcnow()

        user_doc = {
            "name": name.strip(),
            "email": normalized_email,
            "password_hash": password_hash,
            "role": role if role in ["user", "admin"] else "user",
            "preferences": preferences or {
                "favorite_categories": [],
                "receive_notifications": True
            },
            "created_at": now,
            "updated_at": now
        }

        try:
            result = cls.get_collection().insert_one(user_doc)
            user_doc["_id"] = result.inserted_id
            return user_doc
        except DuplicateKeyError as e:
            raise ValueError(f"User with email '{normalized_email}' already exists.") from e
        except OperationFailure as e:
            err_msg = e.details.get("errmsg", str(e)) if hasattr(e, "details") else str(e)
            raise ValueError(f"Document failed schema validation: {err_msg}") from e

    @classmethod
    def get_user_by_id(cls, user_id):
        """Find a user by their ObjectId or hex string representation."""
        oid = to_object_id(user_id)
        return cls.get_collection().find_one({"_id": oid})

    @classmethod
    def get_user_by_email(cls, email):
        """Find a user by their email address."""
        if not email:
            return None
        return cls.get_collection().find_one({"email": email.strip().lower()})

    @classmethod
    def update_user(cls, user_id, update_fields):
        """
        Update user profile fields (e.g. name, preferences, password_hash).
        Prevents updating immutable fields like _id and created_at.
        """
        oid = to_object_id(user_id)
        if not update_fields:
            return cls.get_user_by_id(oid)

        # Protect immutable fields
        sanitized = {k: v for k, v in update_fields.items() if k not in ["_id", "created_at"]}
        if "email" in sanitized and sanitized["email"]:
            sanitized["email"] = sanitized["email"].strip().lower()
        sanitized["updated_at"] = datetime.utcnow()

        try:
            result = cls.get_collection().find_one_and_update(
                {"_id": oid},
                {"$set": sanitized},
                return_document=True
            )
            return result
        except DuplicateKeyError as e:
            raise ValueError(f"Cannot update: email '{sanitized.get('email')}' is already taken.") from e
        except OperationFailure as e:
            err_msg = e.details.get("errmsg", str(e)) if hasattr(e, "details") else str(e)
            raise ValueError(f"Update failed schema validation: {err_msg}") from e

    @classmethod
    def delete_user(cls, user_id):
        """Delete a user document by ID."""
        oid = to_object_id(user_id)
        result = cls.get_collection().delete_one({"_id": oid})
        return result.deleted_count > 0

    @classmethod
    def list_users(cls, role=None, limit=50, skip=0):
        """List users with optional role filter and pagination."""
        filter_query = {}
        if role:
            filter_query["role"] = role
        cursor = cls.get_collection().find(filter_query).skip(skip).limit(limit).sort("created_at", -1)
        return list(cursor)

    # -------------------------------------------------------------
    # Secure Password Reset Workflow (Time-Limited, Single-Use)
    # -------------------------------------------------------------

    @classmethod
    def create_password_reset_token(cls, email, expires_in_minutes=15):
        """
        Generate a secure, random single-use password reset token.
        Stores SHA-256 hash of the token (never plaintext) in the database.
        Returns the raw token string for dispatch or testing.
        """
        if not email or not isinstance(email, str):
            raise ValueError("Email address is required.")

        normalized_email = email.strip().lower()
        user = cls.get_user_by_email(normalized_email)
        if not user:
            raise ValueError(f"No user account found with email '{normalized_email}'.")

        # Invalidate any prior pending reset tokens for this user
        cls.get_resets_collection().update_many(
            {"user_id": user["_id"], "used": False},
            {"$set": {"used": True, "invalidated_at": datetime.utcnow()}}
        )

        # Generate cryptographically secure random token (43 chars URL-safe)
        raw_token = secrets.token_urlsafe(32)

        # Compute SHA-256 hash to avoid storing plaintext token
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        now = datetime.utcnow()
        reset_doc = {
            "user_id": user["_id"],
            "email": normalized_email,
            "token_hash": token_hash,
            "expires_at": now + timedelta(minutes=expires_in_minutes),
            "used": False,
            "used_at": None,
            "created_at": now
        }

        cls.get_resets_collection().insert_one(reset_doc)
        return raw_token

    @classmethod
    def verify_password_reset_token(cls, raw_token):
        """
        Verify a password reset token.
        Enforces single-use and expiration.
        Returns (reset_doc, user) if valid; raises ValueError if invalid, used, or expired.
        """
        if not raw_token or not isinstance(raw_token, str):
            raise ValueError("Password reset token is required.")

        token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
        reset_doc = cls.get_resets_collection().find_one({"token_hash": token_hash})

        if not reset_doc:
            raise ValueError("Invalid or unrecognized password reset token.")

        if reset_doc.get("used"):
            raise ValueError("This password reset token has already been used. Please request a new link.")

        if reset_doc.get("expires_at") < datetime.utcnow():
            raise ValueError("This password reset token has expired. Please request a new link.")

        user = cls.get_user_by_id(reset_doc["user_id"])
        if not user:
            raise ValueError("The user associated with this reset token no longer exists.")

        return reset_doc, user

    @classmethod
    def reset_password_with_token(cls, raw_token, new_password):
        """
        Securely reset user password using a verified single-use token.
        Never stores passwords in plaintext.
        Marks token as used immediately.
        """
        if not new_password or not isinstance(new_password, str) or len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters long.")

        reset_doc, user = cls.verify_password_reset_token(raw_token)

        hashed_password = generate_password_hash(new_password)
        cls.update_user(user["_id"], {"password_hash": hashed_password})

        cls.get_resets_collection().update_one(
            {"_id": reset_doc["_id"]},
            {"$set": {"used": True, "used_at": datetime.utcnow()}}
        )

        return True
