# app/models.py
# Definición de los modelos de la base de datos (tablas).

import uuid
from datetime import datetime
from . import db  # Importamos la instancia db desde __init__.py

class Vehiculo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    placa = db.Column(db.String(20), unique=True, nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    conductor = db.Column(db.String(100), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code_b64 = db.Column(db.Text, nullable=False)
    
    # --- ACTUALIZACIÓN AQUÍ ---
    # Añadimos 'cascade' para que al borrar un vehículo, se borren sus registros de acceso.
    accesos = db.relationship('RegistroAcceso', backref='vehiculo', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Vehiculo {self.placa}>'

class RegistroAcceso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculo.id'), nullable=False)
    # La relación se define ahora en el modelo 'padre' (Vehiculo) a través del backref.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(10), nullable=False) # 'Entrada' o 'Salida'

    def __repr__(self):
        return f'<Registro {self.id} - Vehiculo {self.vehiculo.placa}>'
