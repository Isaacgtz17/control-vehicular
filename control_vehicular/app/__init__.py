# app/__init__.py
# Inicializador del paquete de la aplicación.

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Inicializamos la extensión de la base de datos, pero sin asociarla a una app todavía.
db = SQLAlchemy()

def create_app():
    """
    Crea y configura una instancia de la aplicación Flask.
    Este es el patrón 'Application Factory'.
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- Configuración de la Aplicación ---
    # Ubicación de nuestra base de datos SQLite
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vehiculos.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializamos la base de datos con nuestra aplicación
    db.init_app(app)

    # --- Registro de Blueprints (Rutas) ---
    # Importamos y registramos el blueprint que contiene nuestras rutas.
    # Hacemos la importación aquí para evitar importaciones circulares.
    from . import routes
    app.register_blueprint(routes.main_bp)

    return app
# app/__init__.py
# Inicializador del paquete de la aplicación.

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Inicializamos la extensión de la base de datos, pero sin asociarla a una app todavía.
db = SQLAlchemy()

def create_app():
    """
    Crea y configura una instancia de la aplicación Flask.
    Este es el patrón 'Application Factory'.
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- Configuración de la Aplicación ---
    # Ubicación de nuestra base de datos SQLite
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vehiculos.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializamos la base de datos con nuestra aplicación
    db.init_app(app)

    # --- Registro de Blueprints (Rutas) ---
    # Importamos y registramos el blueprint que contiene nuestras rutas.
    # Hacemos la importación aquí para evitar importaciones circulares.
    from . import routes
    app.register_blueprint(routes.main_bp)

    return app
