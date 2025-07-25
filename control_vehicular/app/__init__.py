# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from datetime import datetime
import pytz

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
socketio = SocketIO()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vehiculos.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev'
    
    # --- NUEVA CONFIGURACIÓN PARA SUBIDA DE FOTOS ---
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'capturas')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True) # Crea la carpeta si no existe

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    @app.template_filter('local_time')
    def local_time_filter(utc_dt):
        if utc_dt is None:
            return ""
        utc_dt = pytz.utc.localize(utc_dt)
        local_tz = pytz.timezone("America/Mexico_City")
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt.strftime('%Y-%m-%d %H:%M:%S')

    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from . import routes
    app.register_blueprint(routes.main_bp)

    from . import auth
    app.register_blueprint(auth.auth_bp)

    return app
