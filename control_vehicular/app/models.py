# app/models.py
import uuid
from datetime import datetime
from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(10), default='vigilante') # 'admin' or 'vigilante'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# NUEVO MODELO PARA LOS OPERADORES
class Operador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)

class Vehiculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_economico = db.Column(db.String(50), unique=True, nullable=False)
    qr_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    placa = db.Column(db.String(20), unique=True, nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    conductor = db.Column(db.String(100), nullable=False) # Conductor principal/default
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code_b64 = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='afuera', nullable=False) # adentro, afuera, mantenimiento
    status_before_maintenance = db.Column(db.String(20), default='afuera', nullable=False)
    accesos = db.relationship('RegistroAcceso', backref='vehiculo', lazy=True, cascade="all, delete-orphan")

class RegistroAcceso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculo.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(10), nullable=False) # Entrada, Salida
    photo_filename = db.Column(db.String(100), nullable=True)
    # CAMPO AÑADIDO: Guarda el nombre del conductor para este acceso específico.
    # Esto es independiente del conductor default del vehículo.
    conductor_asignado = db.Column(db.String(120), nullable=True)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
