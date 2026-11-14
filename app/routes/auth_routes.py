# app/routes/auth_routes.py
"""
Authentication Blueprint for EventSphere.
Handles user registration, login, logout, profile, and secure password reset.
"""

import os
from flask import Blueprint, request, jsonify, session, current_app
from app.services.user_service import UserService
from .auth_helpers import (
    hash_password,
    verify_password,
    login_required,
    get_current_user_id
)

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account. All public registrations default strictly to 'user'."""
    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    preferences = data.get("preferences")

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "error": "Missing required fields: name, email, and password are required."
        }), 400

    # Security: Enforce non-admin role. Public registrations can NEVER create an admin account.
    role = "user"

    password_hash = hash_password(password)

    try:
        user = UserService.create_user(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role,
            preferences=preferences
        )
        # Never expose password hash in response
        user.pop("password_hash", None)
        return jsonify({
            "success": True,
            "message": "User registered successfully.",
            "user": user
        }), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Registration failed: {str(e)}"}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user credentials and initialize session."""
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "success": False,
            "error": "Email and password are required."
        }), 400

    user = UserService.get_user_by_email(email)
    if not user:
        return jsonify({
            "success": False,
            "error": "Invalid email or password."
        }), 401

    if not verify_password(password, user.get("password_hash", "")):
        return jsonify({
            "success": False,
            "error": "Invalid email or password."
        }), 401

    # Initialize Flask session
    session["user_id"] = str(user["_id"])
    session["role"] = user["role"]
    session["user_name"] = user["name"]

    user_info = {
        "_id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "preferences": user.get("preferences", {})
    }

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": user_info
    }), 200

@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    """Clear user session."""
    session.clear()
    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    }), 200

@auth_bp.route("/profile", methods=["GET"])
@login_required
def get_profile():
    """Retrieve profile of the currently logged-in user."""
    user_id = get_current_user_id()
    try:
        user = UserService.get_user_by_id(user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found."}), 404

        user.pop("password_hash", None)
        return jsonify({"success": True, "user": user}), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@auth_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    """Update profile preferences or details for the logged-in user."""
    user_id = get_current_user_id()
    data = request.get_json() or {}

    # Disallow privilege escalation
    data.pop("role", None)
    data.pop("password_hash", None)

    try:
        updated = UserService.update_user(user_id, data)
        if not updated:
            return jsonify({"success": False, "error": "User not found."}), 404

        updated.pop("password_hash", None)
        return jsonify({
            "success": True,
            "message": "Profile updated successfully.",
            "user": updated
        }), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Handle password recovery requests.
    Checks whether email delivery is configured.
    If email delivery is not configured, clearly indicates so rather than pretending an email was sent.
    """
    data = request.get_json() or {}
    email = data.get("email")

    if not email:
        return jsonify({
            "success": False,
            "error": "Email address is required."
        }), 400

    normalized_email = email.strip().lower()
    user = UserService.get_user_by_email(normalized_email)
    if not user:
        return jsonify({
            "success": False,
            "error": "No registered account found with that email address."
        }), 404

    # Check whether email delivery service is configured
    has_smtp = bool(
        current_app.config.get("MAIL_SERVER") or
        os.environ.get("MAIL_SERVER") or
        os.environ.get("SMTP_HOST") or
        os.environ.get("SMTP_SERVER")
    )

    if not has_smtp:
        return jsonify({
            "success": False,
            "email_configured": False,
            "error": "Email delivery service is not configured on this server. Password recovery via email requires SMTP configuration."
        }), 503

    # When SMTP is configured, generate time-limited token and dispatch email
    UserService.create_password_reset_token(normalized_email)
    return jsonify({
        "success": True,
        "email_configured": True,
        "message": "Password reset instructions have been dispatched to your email address."
    }), 200

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Execute password reset using a time-limited, single-use token.
    Never stores passwords or tokens in plaintext.
    """
    data = request.get_json() or {}
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        return jsonify({
            "success": False,
            "error": "Reset token and new password are required."
        }), 400

    try:
        UserService.reset_password_with_token(token, new_password)
        return jsonify({
            "success": True,
            "message": "Password has been successfully reset. You may now sign in with your new password."
        }), 200
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to reset password: {str(e)}"
        }), 500
