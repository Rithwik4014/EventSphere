# app/routes package
from .auth_routes import auth_bp
from .event_routes import events_bp
from .booking_routes import bookings_bp
from .admin_routes import admin_bp
from .web_routes import web_bp

__all__ = ["auth_bp", "events_bp", "bookings_bp", "admin_bp", "web_bp"]
