# app/utils.py
from functools import wraps
from flask import abort
from flask_login import current_user
from . import db
from .models import AuditLog

def log_action(action, details=""):
    """Helper function to log admin actions."""
    if current_user.is_authenticated:
        log = AuditLog(user_id=current_user.id, action=action, details=details)
        db.session.add(log)
        db.session.commit()

def admin_required(f):
    """Decorator to restrict access to admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
