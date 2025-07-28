# app/extensions.py
"""
Este archivo centraliza la inicialización de las extensiones de Flask
para evitar problemas de importación circular.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
