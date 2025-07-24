# app/models.py
# Definición de los modelos de la base de datos (tablas).

import uuid
from datetime import datetime
from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(10), default='vigilante')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Vehiculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    placa = db.Column(db.String(20), unique=True, nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    conductor = db.Column(db.String(100), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code_b64 = db.Column(db.Text, nullable=False)
    
    # --- NUEVO CAMPO DE ESTADO ---
    status = db.Column(db.String(10), default='afuera', nullable=False) # Valores: 'adentro', 'afuera'

    accesos = db.relationship('RegistroAcceso', backref='vehiculo', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Vehiculo {self.placa}>'

class RegistroAcceso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculo.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(10), nullable=False) # 'Entrada' o 'Salida'

    def __repr__(self):
        return f'<Registro {self.id} - Vehiculo {self.vehiculo.placa}>'
