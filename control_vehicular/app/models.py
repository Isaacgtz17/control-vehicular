# app/models.py
import uuid
from datetime import datetime
from .extensions import db
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
    montajes = db.relationship('Montaje', backref='vehiculo', lazy='dynamic')


class RegistroAcceso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculo.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(10), nullable=False)
    photo_filename = db.Column(db.String(100), nullable=True) 
    conductor_asignado = db.Column(db.String(120), nullable=True)
    checklist = db.relationship('ChecklistSalida', backref='registro_acceso', uselist=False, cascade="all, delete-orphan")
    inspecciones_llantas = db.relationship('InspeccionLlanta', backref='registro_acceso', lazy=True)


class ChecklistSalida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registro_acceso_id = db.Column(db.Integer, db.ForeignKey('registro_acceso.id'), nullable=False, unique=True)
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

# ===============================================================
# === MODELOS PARA EL SISTEMA DE CONTROL DE LLANTAS ===
# ===============================================================

class Llanta(db.Model):
    """Representa el inventario de cada llanta individual."""
    id = db.Column(db.Integer, primary_key=True)
    dot_serial = db.Column(db.String(80), unique=True, nullable=False, comment="Identificador único de la llanta")
    marca = db.Column(db.String(80), nullable=False)
    modelo = db.Column(db.String(80), nullable=False)
    medida = db.Column(db.String(50), nullable=False)
    fecha_compra = db.Column(db.Date, nullable=False)
    costo = db.Column(db.Float, nullable=True)
    orden_compra = db.Column(db.String(80), nullable=True) # <-- CAMPO AÑADIDO
    status = db.Column(db.String(30), default='En Bodega', nullable=False) # En Bodega, Montada, Desechada, Renovación
    kilometraje_acumulado = db.Column(db.Float, default=0.0)
    
    montajes = db.relationship('Montaje', backref='llanta', lazy='dynamic')

class PosicionEje(db.Model):
    """Catálogo de las posiciones posibles de las llantas en un vehículo."""
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False, comment="Ej: DI, T1LI...")
    descripcion = db.Column(db.String(100), nullable=False, comment="Ej: Delantera Izquierda, Trasera 1 Izquierda Interior...")

class Montaje(db.Model):
    """Registra el historial de cada vez que una llanta se monta en un vehículo."""
    id = db.Column(db.Integer, primary_key=True)
    llanta_id = db.Column(db.Integer, db.ForeignKey('llanta.id'), nullable=False)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculo.id'), nullable=False)
    posicion_id = db.Column(db.Integer, db.ForeignKey('posicion_eje.id'), nullable=False)
    
    fecha_montaje = db.Column(db.DateTime, default=datetime.utcnow)
    km_montaje = db.Column(db.Float, nullable=False)
    
    fecha_desmontaje = db.Column(db.DateTime, nullable=True)
    km_desmontaje = db.Column(db.Float, nullable=True)
    motivo_desmontaje = db.Column(db.String(200), nullable=True)

    posicion = db.relationship('PosicionEje')
    inspecciones = db.relationship('InspeccionLlanta', backref='montaje', lazy='dynamic')

class InspeccionLlanta(db.Model):
    """Registra una inspección de una llanta en un momento dado."""
    id = db.Column(db.Integer, primary_key=True)
    montaje_id = db.Column(db.Integer, db.ForeignKey('montaje.id'), nullable=False)
    registro_acceso_id = db.Column(db.Integer, db.ForeignKey('registro_acceso.id'), nullable=True)
    
    fecha_inspeccion = db.Column(db.DateTime, default=datetime.utcnow)
    presion_psi = db.Column(db.Integer, nullable=False)
    profundidad_mm = db.Column(db.Float, nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    foto_dano = db.Column(db.String(100), nullable=True)
