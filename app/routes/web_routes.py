# app/routes/web_routes.py
"""
Web Views Blueprint for EventSphere.
Renders Jinja2 HTML pages connected to the frontend client assets and API endpoints.
"""

from flask import Blueprint, render_template

web_bp = Blueprint("web_bp", __name__)

@web_bp.route("/", methods=["GET"])
def home_page():
    return render_template("events/index.html")

@web_bp.route("/events", methods=["GET"])
def events_catalog_page():
    return render_template("events/list.html")

@web_bp.route("/events/create", methods=["GET"])
def create_event_page():
    return render_template("events/form.html")

@web_bp.route("/events/<event_id>", methods=["GET"])
def event_detail_page(event_id):
    return render_template("events/detail.html")

@web_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("auth/login.html")

@web_bp.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    return render_template("auth/forgot_password.html")

@web_bp.route("/reset-password", methods=["GET"])
def reset_password_page():
    return render_template("auth/reset_password.html")

@web_bp.route("/register", methods=["GET"])
def register_page():
    return render_template("auth/register.html")

@web_bp.route("/profile", methods=["GET"])
def profile_page():
    return render_template("auth/profile.html")

@web_bp.route("/my-bookings", methods=["GET"])
def my_bookings_page():
    return render_template("bookings/my_bookings.html")

@web_bp.route("/ticket/<booking_id>", methods=["GET"])
def ticket_page(booking_id):
    return render_template("bookings/ticket.html")

@web_bp.route("/admin/dashboard", methods=["GET"])
def admin_dashboard_page():
    return render_template("admin/dashboard.html")

@web_bp.route("/admin/manage-events", methods=["GET"])
def admin_manage_events_page():
    return render_template("admin/event_manage.html")
