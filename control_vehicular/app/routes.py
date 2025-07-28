# app/routes.py
import base64, qrcode, uuid, csv, io, os
from datetime import datetime
import pytz
from flask import (Blueprint, request, jsonify, render_template, redirect, url_for, 
                   send_file, flash, abort, Response, current_app)
from flask_login import login_required, current_user
from .models import Vehiculo, RegistroAcceso, User, AuditLog, Operador, ChecklistSalida
from . import db, socketio
from .utils import admin_required, log_action

main_bp = Blueprint('main', __name__)

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
        return render_template('dashboard_vigilante.html', **template_data)

@main_bp.route('/vehiculo/toggle_maintenance/<int:vehiculo_id>', methods=['POST'])
@login_required
@admin_required
def toggle_maintenance_status(vehiculo_id):
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    
    if vehiculo.status == 'mantenimiento':
        new_status = vehiculo.status_before_maintenance
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

@main_bp.route('/api/prepare_scan/<qr_id>')
@login_required
def prepare_scan(qr_id):
    vehiculo = Vehiculo.query.filter_by(qr_id=qr_id).first()
    if not vehiculo:
        return jsonify({'status': 'error', 'message': 'Vehículo no reconocido'}), 404

    if vehiculo.status == 'mantenimiento':
        return jsonify({'status': 'denegado', 'message': f'UNIDAD {vehiculo.numero_economico} EN MANTENIMIENTO'}), 403

    if vehiculo.status == 'afuera':
        return jsonify({'status': 'ok', 'action': 'entrada', 'vehiculo': {'placa': vehiculo.placa, 'numero_economico': vehiculo.numero_economico}})
    else:
        operadores = Operador.query.order_by(Operador.nombre).all()
        operadores_list = [{'id': op.id, 'nombre': op.nombre} for op in operadores]
        return jsonify({
            'status': 'ok', 
            'action': 'salida', 
            'vehiculo': {'placa': vehiculo.placa, 'numero_economico': vehiculo.numero_economico},
            'operadores': operadores_list
        })

@main_bp.route('/verificar_qr', methods=['POST'])
def verificar_qr():
    data = request.json
    qr_id = data.get('qr_id')
    conductor_asignado = data.get('conductor_asignado')
    checklist_data = data.get('checklist')
    photo_data = data.get('photo') # Foto de evidencia general

    if not qr_id:
        return jsonify({'status': 'error', 'message': 'Falta el ID del QR'}), 400

    vehiculo = Vehiculo.query.filter_by(qr_id=qr_id).first()
    if not vehiculo:
        return jsonify({'status': 'denegado', 'message': 'Vehículo no reconocido'}), 404
    
    if vehiculo.status == 'afuera':
        tipo_acceso = 'Entrada'
    else:
        tipo_acceso = 'Salida'
        if not conductor_asignado:
             return jsonify({'status': 'error', 'message': 'Debe seleccionar un conductor.'}), 400
        if not checklist_data:
             return jsonify({'status': 'error', 'message': 'Debe completar el checklist de inspección.'}), 400

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_filename = None
    if photo_data:
        try:
            header, encoded = photo_data.split(",", 1)
            photo_bytes = base64.b64decode(encoded)
            photo_filename = f"{vehiculo.placa}_{timestamp_str}_general.jpg"
            photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], photo_filename)
            with open(photo_path, "wb") as f:
                f.write(photo_bytes)
        except Exception as e:
            print(f"Error al guardar foto general: {e}")
            photo_filename = None

    nuevo_registro = RegistroAcceso(
        vehiculo_id=vehiculo.id, 
        tipo=tipo_acceso, 
        photo_filename=photo_filename,
        conductor_asignado=conductor_asignado if tipo_acceso == 'Salida' else None
    )
    db.session.add(nuevo_registro)
    
    if tipo_acceso == 'Salida':
        db.session.flush()
        
        def guardar_foto_falla(item_key, item_data):
            foto_b64 = item_data.get('foto')
            if not foto_b64: return None
            try:
                header, encoded = foto_b64.split(",", 1)
                photo_bytes = base64.b64decode(encoded)
                f_name = f"{vehiculo.placa}_{timestamp_str}_{item_key}.jpg"
                photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f_name)
                with open(photo_path, "wb") as f: f.write(photo_bytes)
                return f_name
            except Exception as e:
                print(f"Error al guardar foto de falla para {item_key}: {e}")
                return None

        nuevo_checklist = ChecklistSalida(
            registro_acceso_id=nuevo_registro.id,
            llantas_estado=checklist_data['llantas']['estado'],
            llantas_obs=checklist_data['llantas'].get('obs'),
            llantas_foto=guardar_foto_falla('llantas', checklist_data['llantas']),
            luces_estado=checklist_data['luces']['estado'],
            luces_obs=checklist_data['luces'].get('obs'),
            luces_foto=guardar_foto_falla('luces', checklist_data['luces']),
            niveles_estado=checklist_data['niveles']['estado'],
            niveles_obs=checklist_data['niveles'].get('obs'),
            niveles_foto=guardar_foto_falla('niveles', checklist_data['niveles']),
            carroceria_estado=checklist_data['carroceria']['estado'],
            carroceria_obs=checklist_data['carroceria'].get('obs'),
            carroceria_foto=guardar_foto_falla('carroceria', checklist_data['carroceria']),
            observaciones_generales=checklist_data.get('generales')
        )
        db.session.add(nuevo_checklist)

    vehiculo.status = 'adentro' if tipo_acceso == 'Entrada' else 'afuera'
    db.session.commit()
    
    # --- LÓGICA DE ACTUALIZACIÓN EN TIEMPO REAL RESTAURADA ---
    unidades_en_patio = Vehiculo.query.filter_by(status='adentro').count()
    unidades_mantenimiento = Vehiculo.query.filter_by(status='mantenimiento').count()
    total_unidades = Vehiculo.query.count()
    unidades_en_ruta = total_unidades - unidades_en_patio - unidades_mantenimiento
    
    local_tz = pytz.timezone("America/Mexico_City")
    local_timestamp = pytz.utc.localize(nuevo_registro.timestamp).astimezone(local_tz)

    update_data = {
        'new_log': {
            'timestamp': local_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'tipo': nuevo_registro.tipo,
            'placa': vehiculo.placa,
            'modelo': vehiculo.modelo,
            'conductor_asignado': nuevo_registro.conductor_asignado,
            'photo_filename': nuevo_registro.photo_filename
        },
        'fleet_status': {
            'en_patio': unidades_en_patio,
            'en_ruta': unidades_en_ruta,
            'mantenimiento': unidades_mantenimiento
        },
        'vehicle_update': {
            'id': vehiculo.id,
            'status': vehiculo.status
        }
    }
    socketio.emit('update_dashboard', update_data)
    
    return jsonify({'status': 'autorizado', 'message': f'{tipo_acceso.upper()} REGISTRADA', 'placa': vehiculo.placa})

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

@main_bp.route('/escaner_movil')
@login_required
def escaner_movil():
    return render_template('escaner_movil.html')

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
