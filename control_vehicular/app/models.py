from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

# Modelo para los usuarios del sistema
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(64), nullable=False, default='vigilante') # Roles: 'admin', 'vigilante'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Modelo para los vehículos
class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    id = db.Column(db.Integer, primary_key=True)
    numero_economico = db.Column(db.String(80), unique=True, nullable=False)
    placa = db.Column(db.String(20), unique=True, nullable=False)
    modelo = db.Column(db.String(80))
    conductor = db.Column(db.String(120))
    qr_id = db.Column(db.String(36), unique=True, nullable=False)
    qr_code_b64 = db.Column(db.Text)
    status = db.Column(db.String(20), default='adentro') # Estados: 'adentro', 'afuera', 'mantenimiento'
    status_before_maintenance = db.Column(db.String(20))
    
    registros = db.relationship('RegistroAcceso', backref='vehiculo', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Vehiculo {self.numero_economico}>'

# Modelo para los operadores/conductores
class Operador(db.Model):
    __tablename__ = 'operadores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True)

    def __repr__(self):
        return f'<Operador {self.nombre}>'

# Modelo principal para la bitácora de entradas y salidas
class RegistroAcceso(db.Model):
    __tablename__ = 'registro_acceso'
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(10), nullable=False)  # 'Entrada' o 'Salida'
    conductor_asignado = db.Column(db.String(120))
    
    # Campo para la foto general (opcional, si aún se quiere mantener)
    photo_filename = db.Column(db.String(255))
    
    # Relación con el checklist de salida
    checklist = db.relationship('ChecklistSalida', backref='registro_acceso', uselist=False, cascade="all, delete-orphan")
    
    # --- LÍNEA AÑADIDA ---
    # Relación con la nueva tabla de evidencias fotográficas
    evidencias = db.relationship('EvidenciaFotografica', backref='registro_acceso', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Registro {self.id} - {self.vehiculo.placa} - {self.tipo}>'

# --- NUEVO MODELO AÑADIDO ---
# Modelo para guardar cada una de las fotos de evidencia
class EvidenciaFotografica(db.Model):
    __tablename__ = 'evidencia_fotografica'
    id = db.Column(db.Integer, primary_key=True)
    registro_acceso_id = db.Column(db.Integer, db.ForeignKey('registro_acceso.id'), nullable=False)
    
    # El tipo de foto, ej: 'frontal_salida', 'lateral_derecho_llegada'
    tipo_foto = db.Column(db.String(50), nullable=False) 
    
    # La ruta donde se guarda la imagen
    url_foto = db.Column(db.String(255), nullable=False)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Evidencia {self.id} - {self.tipo_foto}>'

# Modelo para el checklist detallado que se hace en la salida
class ChecklistSalida(db.Model):
    __tablename__ = 'checklist_salida'
    id = db.Column(db.Integer, primary_key=True)
    registro_acceso_id = db.Column(db.Integer, db.ForeignKey('registro_acceso.id'), nullable=False)
    
    llantas_estado = db.Column(db.String(10)) # ok, falla
    llantas_obs = db.Column(db.Text)
    llantas_foto = db.Column(db.String(255))
    
    luces_estado = db.Column(db.String(10))
    luces_obs = db.Column(db.Text)
    luces_foto = db.Column(db.String(255))
    
    niveles_estado = db.Column(db.String(10))
    niveles_obs = db.Column(db.Text)
    niveles_foto = db.Column(db.String(255))
    
    carroceria_estado = db.Column(db.String(10))
    carroceria_obs = db.Column(db.Text)
    carroceria_foto = db.Column(db.String(255))
    
    observaciones_generales = db.Column(db.Text)

# Modelo para la bitácora de auditoría de acciones importantes
class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(255))
    details = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.action}>'

