# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO # Importamos SocketIO

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
socketio = SocketIO() # Creamos la instancia de SocketIO

def create_app():
    # allow_unsafe_werkzeug es necesario para versiones más recientes
    app = Flask(__name__, instance_relative_config=True)

    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vehiculos.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev'
    
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app) # Inicializamos SocketIO con la app

    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from . import routes
    app.register_blueprint(routes.main_bp)

    from . import auth
    app.register_blueprint(auth.auth_bp)

    return app
