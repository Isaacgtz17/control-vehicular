# app/routes.py
import os
import datetime
import base64
import qrcode
import uuid
import csv
import io
import pytz
from flask import (Blueprint, request, jsonify, render_template, redirect, url_for, 
                   send_file, flash, abort, Response, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

# Asegúrate que los modelos y extensiones se importen correctamente
# Se usan los nombres de tus modelos: Vehiculo, RegistroAcceso, etc.
from .models import (Vehiculo, RegistroAcceso, User, AuditLog, Operador, 
                     ChecklistSalida, EvidenciaFotografica) 
from . import db, socketio
from .utils import admin_required, log_action

# Usamos el blueprint que ya tenías definido
main_bp = Blueprint('main', __name__)

# --- Rutas de Dashboards y Vistas Principales ---

@main_bp.route('/')
@login_required
def index():
    page_vehiculos = request.args.get('page_vehiculos', 1, type=int)
    page_registros = request.args.get('page_registros', 1, type=int)
    q_vehiculo = request.args.get('q_vehiculo', '')
    q_bitacora = request.args.get('q_bitacora', '')

    unidades_en_patio = Vehiculo.query.filter_by(status='adentro').count()
    unidades_mantenimiento = Vehiculo.query.filter_by(status='mantenimiento').count()
    total_unidades = Vehiculo.query.count()
    unidades_en_ruta = total_unidades - unidades_en_patio - unidades_mantenimiento

    if q_vehiculo:
        vehiculos_pagination = Vehiculo.query.filter(
            Vehiculo.placa.contains(q_vehiculo) |
            Vehiculo.modelo.contains(q_vehiculo) |
            Vehiculo.conductor.contains(q_vehiculo) |
            Vehiculo.numero_economico.contains(q_vehiculo)
        ).paginate(page=page_vehiculos, per_page=9)
    else:
        vehiculos_pagination = Vehiculo.query.paginate(page=page_vehiculos, per_page=9)

    if q_bitacora:
        registros_pagination = RegistroAcceso.query.join(Vehiculo).filter(
            Vehiculo.placa.contains(q_bitacora) |
            Vehiculo.modelo.contains(q_bitacora) |
            Vehiculo.conductor.contains(q_bitacora) |
            Vehiculo.numero_economico.contains(q_bitacora)
        ).order_by(RegistroAcceso.timestamp.desc()).paginate(page=page_registros, per_page=10)
    else:
        registros_pagination = RegistroAcceso.query.order_by(RegistroAcceso.timestamp.desc()).paginate(page=page_registros, per_page=10)

    template_data = {
        'vehiculos': vehiculos_pagination,
        'registros': registros_pagination,
        'q_vehiculo': q_vehiculo,
        'q_bitacora': q_bitacora,
        'unidades_en_patio': unidades_en_patio,
        'unidades_en_ruta': unidades_en_ruta,
        'total_unidades': total_unidades,
        'unidades_mantenimiento': unidades_mantenimiento
    }

    if current_user.role == 'admin':
        return render_template('index.html', **template_data)
    else:
        return render_template('dashboard_vigilante.html', registros=registros_pagination)

# --- NUEVO FLUJO DE REVISIÓN CON FOTOS GUIADAS ---

@main_bp.route('/escaner_movil')
@login_required
def escaner_movil():
    """Muestra la página del escáner QR."""
    return render_template('escaner_movil.html')

@main_bp.route('/process-qr', methods=['POST'])
@login_required
def process_qr():
    """
    Recibe el QR, determina si es salida o llegada y redirige al proceso de revisión.
    """
    qr_id = request.form.get('qr_data')
    vehiculo = Vehiculo.query.filter_by(qr_id=qr_id).first()

    if not vehiculo:
        return jsonify({'success': False, 'message': 'Vehículo no encontrado.'})

    if vehiculo.status == 'mantenimiento':
        return jsonify({'success': False, 'message': f'UNIDAD {vehiculo.numero_economico} EN MANTENIMIENTO'})

    # Lógica de SALIDA (el vehículo está 'adentro')
    if vehiculo.status == 'adentro':
        nuevo_registro = RegistroAcceso(vehiculo_id=vehiculo.id, tipo='Salida')
        db.session.add(nuevo_registro)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'redirect_url': url_for('main.check_process', registro_id=nuevo_registro.id, process_type='salida')
        })

    # Lógica de LLEGADA (el vehículo está 'afuera')
    elif vehiculo.status == 'afuera':
        ultimo_registro_salida = RegistroAcceso.query.filter_by(vehiculo_id=vehiculo.id, tipo='Salida').order_by(RegistroAcceso.timestamp.desc()).first()
        
        nuevo_registro_entrada = RegistroAcceso(vehiculo_id=vehiculo.id, tipo='Entrada')
        if ultimo_registro_salida:
            nuevo_registro_entrada.conductor_asignado = ultimo_registro_salida.conductor_asignado
        db.session.add(nuevo_registro_entrada)
        db.session.commit()

        return jsonify({
            'success': True,
            'redirect_url': url_for('main.check_process', registro_id=nuevo_registro_entrada.id, process_type='llegada')
        })
    
    else:
        return jsonify({'success': False, 'message': f'El estado actual del vehículo ({vehiculo.status}) no permite esta operación.'})

@main_bp.route('/check-process/<int:registro_id>/<string:process_type>')
@login_required
def check_process(registro_id, process_type):
    """Muestra la página de checklist para tomar las fotos."""
    registro = RegistroAcceso.query.get_or_404(registro_id)
    vehiculo = registro.vehiculo
    return render_template('check_process.html', registro_id=registro.id, vehiculo=vehiculo, process_type=process_type)

@main_bp.route('/upload-check-photo', methods=['POST'])
@login_required
def upload_check_photo():
    """Recibe y guarda una foto de evidencia para un registro específico."""
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'No se encontró el archivo de la foto.'})

    file = request.files['photo']
    registro_id = request.form.get('registro_id')
    photo_type = request.form.get('photo_type')

    if not all([file, registro_id, photo_type]):
        return jsonify({'success': False, 'message': 'Faltan datos para subir la foto.'})

    try:
        filename = secure_filename(f"{registro_id}_{photo_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        nueva_evidencia = EvidenciaFotografica(
            registro_acceso_id=registro_id, 
            tipo_foto=photo_type, 
            url_foto=filename
        )
        db.session.add(nueva_evidencia)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Foto guardada.', 'photo_url': filename})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al guardar foto: {e}")
        return jsonify({'success': False, 'message': 'Error interno al guardar la foto.'})

@main_bp.route('/finish-check/<int:registro_id>')
@login_required
def finish_check(registro_id):
    """Finaliza el proceso de revisión y actualiza el estado del vehículo."""
    registro = RegistroAcceso.query.get_or_404(registro_id)
    vehiculo = registro.vehiculo
    
    if registro.tipo == 'Salida':
        vehiculo.status = 'afuera'
        action_log_msg = f'Completó revisión de SALIDA para vehículo {vehiculo.numero_economico}'
        log_action("Revisión Salida", f"Vehículo: {vehiculo.numero_economico}")
    elif registro.tipo == 'Entrada':
        vehiculo.status = 'adentro'
        action_log_msg = f'Completó revisión de LLEGADA para vehículo {vehiculo.numero_economico}'
        log_action("Revisión Entrada", f"Vehículo: {vehiculo.numero_economico}")
    
    db.session.commit()
    
    unidades_en_patio = Vehiculo.query.filter_by(status='adentro').count()
    unidades_mantenimiento = Vehiculo.query.filter_by(status='mantenimiento').count()
    total_unidades = Vehiculo.query.count()
    unidades_en_ruta = total_unidades - unidades_en_patio - unidades_mantenimiento
    
    update_data = {
        'fleet_status': { 'en_patio': unidades_en_patio, 'en_ruta': unidades_en_ruta, 'mantenimiento': unidades_mantenimiento },
        'vehicle_update': { 'id': vehiculo.id, 'status': vehiculo.status }
    }
    socketio.emit('update_dashboard', update_data)
    
    flash(f'Proceso para el vehículo {vehiculo.numero_economico} finalizado con éxito.', 'success')
    return redirect(url_for('main.index'))

# --- RUTAS DE GESTIÓN Y OTRAS (CÓDIGO ORIGINAL) ---

@main_bp.route('/vehiculo/toggle_maintenance/<int:vehiculo_id>', methods=['POST'])
@login_required
@admin_required
def toggle_maintenance_status(vehiculo_id):
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    if vehiculo.status == 'mantenimiento':
        new_status = vehiculo.status_before_maintenance or 'adentro'
    else:
        vehiculo.status_before_maintenance = vehiculo.status
        new_status = 'mantenimiento'
    old_status = vehiculo.status
    vehiculo.status = new_status
    db.session.commit()
    log_action("Cambio de Estado Manual", f"Unidad {vehiculo.numero_economico}: de '{old_status}' a '{new_status}'")
    
    unidades_en_patio = Vehiculo.query.filter_by(status='adentro').count()
    unidades_mantenimiento = Vehiculo.query.filter_by(status='mantenimiento').count()
    total_unidades = Vehiculo.query.count()
    unidades_en_ruta = total_unidades - unidades_en_patio - unidades_mantenimiento
    
    update_data = {
        'fleet_status': { 'en_patio': unidades_en_patio, 'en_ruta': unidades_en_ruta, 'mantenimiento': unidades_mantenimiento },
        'vehicle_update': { 'id': vehiculo.id, 'status': vehiculo.status }
    }
    socketio.emit('update_dashboard', update_data)
    return jsonify({'status': 'success', 'message': f'Estado de {vehiculo.numero_economico} actualizado.'})

@main_bp.route('/vehiculo/historial/<int:vehiculo_id>')
@login_required
@admin_required
def historial_vehiculo(vehiculo_id):
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    registros = RegistroAcceso.query.filter_by(vehiculo_id=vehiculo.id).order_by(RegistroAcceso.timestamp.desc()).all()
    historial = []
    local_tz = pytz.timezone("America/Mexico_City")
    for registro in registros:
        utc_dt = pytz.utc.localize(registro.timestamp)
        local_dt = utc_dt.astimezone(local_tz)
        
        checklist_info = None
        if registro.checklist:
            checklist_info = {
                'llantas': {'estado': registro.checklist.llantas_estado, 'obs': registro.checklist.llantas_obs, 'foto': registro.checklist.llantas_foto},
                'luces': {'estado': registro.checklist.luces_estado, 'obs': registro.checklist.luces_obs, 'foto': registro.checklist.luces_foto},
                'niveles': {'estado': registro.checklist.niveles_estado, 'obs': registro.checklist.niveles_obs, 'foto': registro.checklist.niveles_foto},
                'carroceria': {'estado': registro.checklist.carroceria_estado, 'obs': registro.checklist.carroceria_obs, 'foto': registro.checklist.carroceria_foto},
                'generales': registro.checklist.observaciones_generales
            }

        historial.append({
            'timestamp': local_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'tipo': registro.tipo,
            'photo_filename': registro.photo_filename,
            'conductor_asignado': registro.conductor_asignado,
            'checklist': checklist_info
        })
    return jsonify({
        'placa': vehiculo.placa, 'modelo': vehiculo.modelo, 'conductor': vehiculo.conductor, 
        'historial': historial, 'numero_economico': vehiculo.numero_economico
    })

@main_bp.route('/registrar_vehiculo', methods=['POST'])
@login_required
@admin_required
def registrar_vehiculo():
    numero_economico = request.form['numero_economico']
    placa = request.form['placa']
    
    if Vehiculo.query.filter_by(placa=placa).first() or \
       Vehiculo.query.filter_by(numero_economico=numero_economico).first():
        flash(f'La placa "{placa}" o el No. Económico "{numero_economico}" ya existen.', 'error')
        return redirect(url_for('main.index'))

    modelo = request.form['modelo']
    conductor = request.form['conductor']
    qr_id_nuevo = str(uuid.uuid4())
    qr_img = qrcode.make(qr_id_nuevo)
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    nuevo_vehiculo = Vehiculo(
        numero_economico=numero_economico, 
        qr_id=qr_id_nuevo, 
        placa=placa, 
        modelo=modelo, 
        conductor=conductor, 
        qr_code_b64=qr_b64
    )
    db.session.add(nuevo_vehiculo)
    db.session.commit()
    log_action("Crear Vehículo", f"No. Económico: {numero_economico}, Placa: {placa}")
    flash(f'Unidad {numero_economico} registrada.', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/vehiculo/editar/<int:vehiculo_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_vehiculo(vehiculo_id):
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    if request.method == 'POST':
        vehiculo.numero_economico = request.form['numero_economico']
        vehiculo.placa = request.form['placa']
        vehiculo.modelo = request.form['modelo']
        vehiculo.conductor = request.form['conductor']
        db.session.commit()
        log_action("Editar Vehículo", f"No. Económico: {vehiculo.numero_economico}")
        flash(f'Unidad {vehiculo.numero_economico} actualizada.', 'success')
        return redirect(url_for('main.index'))
    return render_template('editar_vehiculo.html', vehiculo=vehiculo)

@main_bp.route('/vehiculo/eliminar/<int:vehiculo_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_vehiculo(vehiculo_id):
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    placa_eliminada = vehiculo.placa
    db.session.delete(vehiculo)
    db.session.commit()
    log_action("Eliminar Vehículo", f"Placa: {placa_eliminada}")
    flash(f'Vehículo {placa_eliminada} ha sido eliminado.', 'success')
    return redirect(url_for('main.index'))

@main_bp.route('/vehiculo/descargar_qr/<int:vehiculo_id>')
@login_required
@admin_required
def descargar_qr(vehiculo_id):
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    qr_img = qrcode.make(vehiculo.qr_id)
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    buffered.seek(0)
    return send_file(
        buffered, 
        download_name=f"qr_{vehiculo.placa}.png", 
        mimetype='image/png',
        as_attachment=True
    )

@main_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@main_bp.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        if User.query.filter_by(username=username).first():
            flash('Ese nombre de usuario ya existe.', 'error')
        else:
            new_user = User(username=username, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            log_action("Crear Usuario", f"Username: {username}, Rol: {role}")
            flash('Usuario creado exitosamente.', 'success')
            return redirect(url_for('main.manage_users'))
    return render_template('user_form.html')

@main_bp.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.role = request.form.get('role')
        password = request.form.get('password')
        if password:
            user.set_password(password)
        db.session.commit()
        log_action("Editar Usuario", f"Username: {user.username}")
        flash('Usuario actualizado.', 'success')
        return redirect(url_for('main.manage_users'))
    return render_template('user_form.html', user=user)

@main_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('No puedes eliminarte a ti mismo.', 'error')
        return redirect(url_for('main.manage_users'))
    user = User.query.get_or_404(user_id)
    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_action("Eliminar Usuario", f"Username: {username}")
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('main.manage_users'))

@main_bp.route('/reports')
@login_required
@admin_required
def reports():
    return render_template('reports.html')

@main_bp.route('/export_csv', methods=['POST'])
@login_required
@admin_required
def export_csv():
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(f"{end_date_str} 23:59:59", '%Y-%m-%d %H:%M:%S')

    registros = RegistroAcceso.query.filter(
        RegistroAcceso.timestamp >= start_date,
        RegistroAcceso.timestamp <= end_date
    ).order_by(RegistroAcceso.timestamp.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Fecha y Hora', 'Tipo', 'Placa', 'Modelo', 'Conductor Asignado'])
    for registro in registros:
        writer.writerow([
            registro.id, 
            registro.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 
            registro.tipo, 
            registro.vehiculo.placa, 
            registro.vehiculo.modelo, 
            registro.conductor_asignado or 'N/A'
        ])
    
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=reporte_accesos_{start_date_str}_a_{end_date_str}.csv"}
    )

@main_bp.route('/audit_log')
@login_required
@admin_required
def audit_log():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=20)
    return render_template('audit_log.html', logs=logs)
