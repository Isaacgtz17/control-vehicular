# app/llantas_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from .models import Llanta, Vehiculo, PosicionEje, Montaje
from . import db
from .utils import admin_required, log_action
from datetime import datetime

llantas_bp = Blueprint('llantas', __name__, url_prefix='/llantas')

@llantas_bp.route('/')
@login_required
@admin_required
def inventario():
    """Muestra el inventario de todas las llantas."""
    llantas = Llanta.query.order_by(Llanta.marca, Llanta.modelo).all()
    return render_template('llantas_inventario.html', llantas=llantas)

@llantas_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
@admin_required
def anadir_llanta():
    """Maneja la creación de una nueva llanta en el inventario."""
    if request.method == 'POST':
        dot_serial = request.form.get('dot_serial')
        if Llanta.query.filter_by(dot_serial=dot_serial).first():
            flash(f'El DOT/Serial "{dot_serial}" ya está registrado.', 'error')
            return render_template('llanta_form.html', title="Añadir Nueva Llanta")

        try:
            nueva_llanta = Llanta(
                dot_serial=dot_serial,
                marca=request.form.get('marca'),
                modelo=request.form.get('modelo'),
                medida=request.form.get('medida'),
                fecha_compra=datetime.strptime(request.form.get('fecha_compra'), '%Y-%m-%d').date(),
                costo=float(request.form.get('costo')),
                orden_compra=request.form.get('orden_compra')
            )
            db.session.add(nueva_llanta)
            db.session.commit()
            log_action("Crear Llanta", f"DOT/Serial: {dot_serial}")
            flash('Llanta registrada en el inventario exitosamente.', 'success')
            return redirect(url_for('llantas.inventario'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar la llanta: {e}', 'error')

    return render_template('llanta_form.html', title="Añadir Nueva Llanta")

@llantas_bp.route('/vehiculo/<int:vehiculo_id>')
@login_required
@admin_required
def gestionar_vehiculo(vehiculo_id):
    """Página principal para gestionar las llantas de un vehículo específico."""
    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
    posiciones = PosicionEje.query.all()
    llantas_bodega = Llanta.query.filter_by(status='En Bodega').all()
    
    # Obtener los montajes activos para este vehículo
    montajes_activos = Montaje.query.filter_by(vehiculo_id=vehiculo.id, fecha_desmontaje=None).all()
    
    # Crear un diccionario para fácil acceso en la plantilla: {posicion_id: montaje_obj}
    mapa_posiciones = {montaje.posicion_id: montaje for montaje in montajes_activos}

    return render_template('vehiculo_llantas.html', 
                           vehiculo=vehiculo, 
                           posiciones=posiciones, 
                           llantas_bodega=llantas_bodega,
                           mapa_posiciones=mapa_posiciones)

@llantas_bp.route('/montar', methods=['POST'])
@login_required
@admin_required
def montar_llanta():
    """Endpoint para procesar el montaje de una llanta."""
    data = request.json
    try:
        vehiculo_id = int(data['vehiculo_id'])
        llanta_id = int(data['llanta_id'])
        posicion_id = int(data['posicion_id'])
        km_actual = float(data['km_actual'])

        llanta = Llanta.query.get_or_404(llanta_id)
        if llanta.status != 'En Bodega':
            return jsonify({'status': 'error', 'message': 'La llanta seleccionada no está en bodega.'}), 400

        # Crear nuevo montaje
        nuevo_montaje = Montaje(
            vehiculo_id=vehiculo_id,
            llanta_id=llanta_id,
            posicion_id=posicion_id,
            km_montaje=km_actual
        )
        
        # Actualizar estado de la llanta
        llanta.status = 'Montada'
        
        db.session.add(nuevo_montaje)
        db.session.commit()
        
        log_action("Montaje Llanta", f"Llanta {llanta.dot_serial} en Vehículo ID {vehiculo_id}, Posición ID {posicion_id}")
        flash('Llanta montada exitosamente.', 'success')
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@llantas_bp.route('/desmontar', methods=['POST'])
@login_required
@admin_required
def desmontar_llanta():
    """Endpoint para procesar el desmontaje de una llanta."""
    data = request.json
    try:
        montaje_id = int(data['montaje_id'])
        km_actual = float(data['km_actual'])
        motivo = data['motivo']
        nuevo_status = data['nuevo_status']

        montaje = Montaje.query.get_or_404(montaje_id)
        if montaje.fecha_desmontaje is not None:
             return jsonify({'status': 'error', 'message': 'Esta llanta ya fue desmontada.'}), 400

        # Actualizar el registro de montaje
        montaje.fecha_desmontaje = datetime.utcnow()
        montaje.km_desmontaje = km_actual
        montaje.motivo_desmontaje = motivo
        
        # Actualizar la llanta
        llanta = montaje.llanta
        km_recorridos = km_actual - montaje.km_montaje
        if km_recorridos > 0:
            llanta.kilometraje_acumulado += km_recorridos
        llanta.status = nuevo_status
        
        db.session.commit()

        log_action("Desmontaje Llanta", f"Llanta {llanta.dot_serial} de Vehículo ID {montaje.vehiculo_id}. Motivo: {motivo}")
        flash('Llanta desmontada exitosamente.', 'success')
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
