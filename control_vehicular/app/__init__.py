# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager # Importamos el LoginManager

db = SQLAlchemy()
login_manager = LoginManager() # Creamos la instancia del manejador
login_manager.login_view = 'auth.login' # Le decimos cuál es la página de login

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vehiculos.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'dev'
    
    db.init_app(app)
    login_manager.init_app(app) # Inicializamos el manejador con la app

    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Importamos y registramos los blueprints
    from . import routes
    app.register_blueprint(routes.main_bp)

    from . import auth # Importamos el nuevo archivo de autenticación
    app.register_blueprint(auth.auth_bp)

    return app
