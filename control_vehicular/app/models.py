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
    role = db.Column(db.String(10), default='vigilante')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Operador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), unique=True, nullable=False)

class Vehiculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_economico = db.Column(db.String(50), unique=True, nullable=False)
    qr_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    placa = db.Column(db.String(20), unique=True, nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    conductor = db.Column(db.String(100), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code_b64 = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='afuera', nullable=False)
    status_before_maintenance = db.Column(db.String(20), default='afuera', nullable=False)
    accesos = db.relationship('RegistroAcceso', backref='vehiculo', lazy=True, cascade="all, delete-orphan")

class RegistroAcceso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculo.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(10), nullable=False)
    photo_filename = db.Column(db.String(100), nullable=True) # Foto general de evidencia
    conductor_asignado = db.Column(db.String(120), nullable=True)
    # Relación uno a uno con el checklist
    checklist = db.relationship('ChecklistSalida', backref='registro_acceso', uselist=False, cascade="all, delete-orphan")

# --- NUEVA TABLA PARA LA BITÁCORA DE INSPECCIÓN ---
class ChecklistSalida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Clave foránea para vincular con un registro de acceso específico
    registro_acceso_id = db.Column(db.Integer, db.ForeignKey('registro_acceso.id'), nullable=False, unique=True)
    
    # --- Puntos del Checklist ---
    # Guardaremos el estado: 'ok', 'falla'
    llantas_estado = db.Column(db.String(10), nullable=False)
    llantas_foto = db.Column(db.String(100), nullable=True)
    llantas_obs = db.Column(db.Text, nullable=True)
    
    luces_estado = db.Column(db.String(10), nullable=False)
    luces_foto = db.Column(db.String(100), nullable=True)
    luces_obs = db.Column(db.Text, nullable=True)

    niveles_estado = db.Column(db.String(10), nullable=False)
    niveles_foto = db.Column(db.String(100), nullable=True)
    niveles_obs = db.Column(db.Text, nullable=True)

    carroceria_estado = db.Column(db.String(10), nullable=False)
    carroceria_foto = db.Column(db.String(100), nullable=True)
    carroceria_obs = db.Column(db.Text, nullable=True)
    
    observaciones_generales = db.Column(db.Text, nullable=True)


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
