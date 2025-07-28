# app/catalog.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .models import Operador
from . import db
from .routes import admin_required, log_action

catalog_bp = Blueprint('catalog', __name__, url_prefix='/catalog')

@catalog_bp.route('/')
@login_required
@admin_required
def index():
    """Página principal del catálogo."""
    return render_template('catalog_index.html')

# --- Rutas para la Gestión de Operadores ---

@catalog_bp.route('/operators')
@login_required
@admin_required
def manage_operators():
    """Muestra la lista de todos los operadores."""
    operators = Operador.query.order_by(Operador.nombre).all()
    return render_template('manage_operators.html', operators=operators)

@catalog_bp.route('/operators/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_operator():
    """Muestra el formulario para añadir un nuevo operador y procesa el envío."""
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if not nombre:
            flash('El nombre del operador no puede estar vacío.', 'error')
        elif Operador.query.filter_by(nombre=nombre).first():
            flash('Ese nombre de operador ya existe.', 'error')
        else:
            new_operator = Operador(nombre=nombre)
            db.session.add(new_operator)
            db.session.commit()
            log_action("Crear Operador", f"Nombre: {nombre}")
            flash('Operador añadido exitosamente.', 'success')
            return redirect(url_for('catalog.manage_operators'))
    return render_template('operator_form.html', title="Añadir Operador")

@catalog_bp.route('/operators/edit/<int:operator_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_operator(operator_id):
    """Muestra el formulario para editar un operador y procesa el envío."""
    operator = Operador.query.get_or_404(operator_id)
    if request.method == 'POST':
        nuevo_nombre = request.form.get('nombre')
        if not nuevo_nombre:
            flash('El nombre del operador no puede estar vacío.', 'error')
        elif Operador.query.filter(Operador.nombre == nuevo_nombre, Operador.id != operator_id).first():
            flash('Ese nombre de operador ya está en uso.', 'error')
        else:
            old_name = operator.nombre
            operator.nombre = nuevo_nombre
            db.session.commit()
            log_action("Editar Operador", f"ID: {operator.id}, Nombre anterior: '{old_name}', Nombre nuevo: '{nuevo_nombre}'")
            flash('Operador actualizado exitosamente.', 'success')
            return redirect(url_for('catalog.manage_operators'))
    return render_template('operator_form.html', title="Editar Operador", operator=operator)

@catalog_bp.route('/operators/delete/<int:operator_id>', methods=['POST'])
@login_required
@admin_required
def delete_operator(operator_id):
    """Elimina un operador de la base de datos."""
    operator = Operador.query.get_or_404(operator_id)
    nombre_eliminado = operator.nombre
    db.session.delete(operator)
    db.session.commit()
    log_action("Eliminar Operador", f"Nombre: {nombre_eliminado}")
    flash(f'Operador "{nombre_eliminado}" ha sido eliminado.', 'success')
    return redirect(url_for('catalog.manage_operators'))
