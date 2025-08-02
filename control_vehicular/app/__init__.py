# app/__init__.py
import os
from flask import Flask
from datetime import datetime
import pytz

from .extensions import db, login_manager, socketio, migrate, limiter

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # --- Configuración de la App ---
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vehiculos.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev' 
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'capturas')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- Inicialización de Extensiones ---
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # --- Filtros de Plantillas y Loaders ---
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

    # --- Registro de Blueprints ---
    from .routes import main_bp
    app.register_blueprint(main_bp)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .catalog import catalog_bp
    app.register_blueprint(catalog_bp)

    from .llantas_routes import llantas_bp
    app.register_blueprint(llantas_bp)
    
    # --- NUEVO BLUEPRINT PARA GEOTAB ---
    from .geotab_routes import geotab_bp
    app.register_blueprint(geotab_bp)

    return app
