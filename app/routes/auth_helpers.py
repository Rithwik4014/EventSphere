# app/routes/auth_helpers.py
"""
Authentication and Authorization Helpers.
Includes session/header-based route decorators and password hashing.
"""

from functools import wraps
from flask import session, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password: str) -> str:
    """Generate a secure salted password hash using Werkzeug."""
    return generate_password_hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain password against a stored hash."""
    return check_password_hash(password_hash, password)

def get_current_user_id():
    """Retrieve current user ID from header (API) or session."""
    return request.headers.get("X-User-Id") or session.get("user_id")

def get_current_user_role():
    """Retrieve current user role from header (API) or session."""
    return request.headers.get("X-User-Role") or session.get("role")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in."
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in."
            }), 401
        role = get_current_user_role()
        if role != "admin":
            return jsonify({
                "success": False,
                "error": "Admin privileges required."
            }), 403
        return f(*args, **kwargs)
    return decorated_function
