# app/routes.py
# Lógica de las rutas y vistas de la aplicación.

import base64
import qrcode
import uuid
from io import BytesIO
from datetime import datetime
# Importamos 'send_file' para la descarga de archivos.
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, send_file

from .models import Vehiculo, RegistroAcceso
from . import db

# Creamos un Blueprint. Es como una mini-app dentro de nuestra app principal.
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    vehiculos = Vehiculo.query.all()
    registros = RegistroAcceso.query.order_by(RegistroAcceso.timestamp.desc()).all()
    return render_template('index.html', vehiculos=vehiculos, registros=registros)

@main_bp.route('/registrar_vehiculo', methods=['POST'])
def registrar_vehiculo():
    placa = request.form['placa']
    modelo = request.form['modelo']
    conductor = request.form['conductor']

    if Vehiculo.query.filter_by(placa=placa).first():
        return redirect(url_for('main.index'))

    qr_id_nuevo = str(uuid.uuid4())
    qr_img = qrcode.make(qr_id_nuevo)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    nuevo_vehiculo = Vehiculo(
        qr_id=qr_id_nuevo,
        placa=placa,
        modelo=modelo,
        conductor=conductor,
        qr_code_b64=qr_b64
    )
    
    db.session.add(nuevo_vehiculo)
    db.session.commit()
    
    return redirect(url_for('main.index'))

@main_bp.route('/verificar_qr', methods=['POST'])
def verificar_qr():
    data = request.json
    if not data or 'qr_id' not in data:
        return jsonify({'status': 'error', 'message': 'Datos inválidos'}), 400

    qr_id_recibido = data['qr_id']
    vehiculo = Vehiculo.query.filter_by(qr_id=qr_id_recibido).first()

    if vehiculo:
        nuevo_registro = RegistroAcceso(vehiculo_id=vehiculo.id, tipo='Entrada')
        db.session.add(nuevo_registro)
        db.session.commit()
        
        return jsonify({
            'status': 'autorizado',
            'placa': vehiculo.placa,
            'modelo': vehiculo.modelo,
            'conductor': vehiculo.conductor,
            'timestamp': datetime.utcnow().isoformat()
        })
    else:
        return jsonify({'status': 'denegado', 'message': 'Vehículo no reconocido'}), 404

# --- NUEVA RUTA PARA ELIMINAR VEHÍCULOS ---
@main_bp.route('/vehiculo/eliminar/<int:vehiculo_id>', methods=['POST'])
def eliminar_vehiculo(vehiculo_id):
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    db.session.delete(vehiculo)
    db.session.commit()
    return redirect(url_for('main.index'))

# --- NUEVA RUTA PARA DESCARGAR EL CÓDIGO QR ---
@main_bp.route('/vehiculo/descargar_qr/<int:vehiculo_id>')
def descargar_qr(vehiculo_id):
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    
    # Generamos la imagen del QR en memoria
    qr_img = qrcode.make(vehiculo.qr_id)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    buffered.seek(0) # Regresamos el cursor al inicio del buffer

    # Enviamos el archivo para su descarga
    return send_file(
        buffered,
        download_name=f"qr_{vehiculo.placa}.png",
        mimetype='image/png',
        as_attachment=True
    )
