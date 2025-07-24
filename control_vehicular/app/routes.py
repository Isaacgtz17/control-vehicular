# app/routes.py
import base64
import qrcode
import uuid
from io import BytesIO
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, send_file, flash, abort
from flask_login import login_required, current_user # Importamos herramientas de login
from functools import wraps # Para crear nuestro decorador

from .models import Vehiculo, RegistroAcceso
from . import db

main_bp = Blueprint('main', __name__)

# --- NUEVO DECORADOR PARA REQUERIR ROL DE ADMIN ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            abort(403) # Error de Acceso Prohibido
        return f(*args, **kwargs)
    return decorated_function

# Aplicamos @login_required a todas las rutas de este blueprint
@main_bp.before_request
@login_required
def before_request():
    pass

@main_bp.route('/')
def index():
    # ... (la lógica de búsqueda se queda igual)
    q_vehiculo = request.args.get('q_vehiculo', '')
    q_bitacora = request.args.get('q_bitacora', '')
    if q_vehiculo:
        vehiculos = Vehiculo.query.filter(Vehiculo.placa.contains(q_vehiculo) | Vehiculo.modelo.contains(q_vehiculo) | Vehiculo.conductor.contains(q_vehiculo)).all()
    else:
        vehiculos = Vehiculo.query.all()
    if q_bitacora:
        registros = RegistroAcceso.query.join(Vehiculo).filter(Vehiculo.placa.contains(q_bitacora) | Vehiculo.modelo.contains(q_bitacora) | Vehiculo.conductor.contains(q_bitacora)).order_by(RegistroAcceso.timestamp.desc()).all()
    else:
        registros = RegistroAcceso.query.order_by(RegistroAcceso.timestamp.desc()).all()
    return render_template('index.html', vehiculos=vehiculos, registros=registros, q_vehiculo=q_vehiculo, q_bitacora=q_bitacora)

@main_bp.route('/registrar_vehiculo', methods=['POST'])
@admin_required # Solo los admins pueden registrar
def registrar_vehiculo():
    # ... (la lógica interna no cambia)
    placa = request.form['placa']
    if Vehiculo.query.filter_by(placa=placa).first():
        flash(f'La placa "{placa}" ya existe en la base de datos.', 'error')
        return redirect(url_for('main.index'))
    modelo = request.form['modelo']
    conductor = request.form['conductor']
    qr_id_nuevo = str(uuid.uuid4())
    qr_img = qrcode.make(qr_id_nuevo)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    nuevo_vehiculo = Vehiculo(qr_id=qr_id_nuevo, placa=placa, modelo=modelo, conductor=conductor, qr_code_b64=qr_b64)
    db.session.add(nuevo_vehiculo)
    db.session.commit()
    flash(f'Vehículo con placa "{placa}" registrado con éxito.', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/vehiculo/editar/<int:vehiculo_id>', methods=['GET', 'POST'])
@admin_required # Solo los admins pueden editar
def editar_vehiculo(vehiculo_id):
    # ... (la lógica interna no cambia)
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    if request.method == 'POST':
        vehiculo.placa = request.form['placa']
        vehiculo.modelo = request.form['modelo']
        vehiculo.conductor = request.form['conductor']
        db.session.commit()
        flash(f'Vehículo con placa "{vehiculo.placa}" actualizado correctamente.', 'success')
        return redirect(url_for('main.index'))
    return render_template('editar_vehiculo.html', vehiculo=vehiculo)

@main_bp.route('/vehiculo/eliminar/<int:vehiculo_id>', methods=['POST'])
@admin_required # Solo los admins pueden eliminar
def eliminar_vehiculo(vehiculo_id):
    # ... (la lógica interna no cambia)
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    placa_eliminada = vehiculo.placa
    db.session.delete(vehiculo)
    db.session.commit()
    flash(f'Vehículo con placa "{placa_eliminada}" ha sido eliminado.', 'success')
    return redirect(url_for('main.index'))

# La verificación de QR no necesita @admin_required, pero sí @login_required (que ya se aplica a todo el blueprint)
@main_bp.route('/verificar_qr', methods=['POST'])
def verificar_qr():
    # ... (la lógica interna no cambia)
    data = request.json
    if not data or 'qr_id' not in data:
        return jsonify({'status': 'error', 'message': 'Datos inválidos'}), 400
    qr_id_recibido = data['qr_id']
    vehiculo = Vehiculo.query.filter_by(qr_id=qr_id_recibido).first()
    if vehiculo:
        nuevo_registro = RegistroAcceso(vehiculo_id=vehiculo.id, tipo='Entrada')
        db.session.add(nuevo_registro)
        db.session.commit()
        return jsonify({'status': 'autorizado','placa': vehiculo.placa,'modelo': vehiculo.modelo,'conductor': vehiculo.conductor,'timestamp': datetime.utcnow().isoformat()})
    else:
        return jsonify({'status': 'denegado', 'message': 'Vehículo no reconocido'}), 404

# La descarga tampoco necesita ser solo de admin
@main_bp.route('/vehiculo/descargar_qr/<int:vehiculo_id>')
def descargar_qr(vehiculo_id):
    # ... (la lógica interna no cambia)
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    qr_img = qrcode.make(vehiculo.qr_id)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    buffered.seek(0)
    return send_file(buffered,download_name=f"qr_{vehiculo.placa}.png",mimetype='image/png',as_attachment=True)
