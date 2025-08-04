# run.py
import click
import csv
import base64
import qrcode
import io
import uuid
from app import create_app, db, socketio
from app.models import User, Vehiculo, Operador

app = create_app()

# --- Comandos CLI para gestión ---

@app.cli.command("create-initial-users")
def create_initial_users():
    """Crea los usuarios iniciales 'admin' y 'vigilante' con contraseñas por defecto."""
    with app.app_context():
        print("Creando usuarios iniciales...")
        # Revisa si el usuario admin ya existe
        if User.query.filter_by(username='admin').first():
            print("El usuario 'admin' ya existe. Omitiendo.")
        else:
            admin_user = User(username='admin', role='admin')
            admin_user.set_password('admin123') # ¡IMPORTANTE: Cambiar esta contraseña en producción!
            db.session.add(admin_user)
            print("Usuario 'admin' creado con contraseña 'admin123'.")

        # Revisa si el usuario vigilante ya existe
        if User.query.filter_by(username='vigilante').first():
            print("El usuario 'vigilante' ya existe. Omitiendo.")
        else:
            vigilante_user = User(username='vigilante', role='vigilante')
            vigilante_user.set_password('vigilante123') # ¡IMPORTANTE: Cambiar esta contraseña en producción!
            db.session.add(vigilante_user)
            print("Usuario 'vigilante' creado con contraseña 'vigilante123'.")
        
        db.session.commit()
        print("¡Proceso de creación de usuarios iniciales finalizado!")


@app.cli.command("create-user")
@click.argument("username")
@click.argument("password")
@click.option("--role", default="vigilante", help="Rol del usuario (admin o vigilante)")
def create_user(username, password, role):
    """Crea un nuevo usuario personalizado en la base de datos."""
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print(f"El usuario {username} ya existe.")
            return

        if role not in ['admin', 'vigilante']:
            print("Rol inválido. Debe ser 'admin' o 'vigilante'.")
            return

        new_user = User(username=username, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        print(f"Usuario {username} con rol {role} creado exitosamente.")

@app.cli.command("import-vehicles")
@click.argument("filepath", type=click.Path(exists=True))
def import_vehicles(filepath):
    """Importa vehículos desde un archivo CSV."""
    with app.app_context():
        try:
            with open(filepath, mode='r', encoding='utf-8') as csv_file:
                csv_reader = csv.reader(csv_file)
                next(csv_reader)  # Skip header
                next(csv_reader)  # Skip header
                print("Iniciando importación de vehículos...")
                imported_count = 0
                skipped_count = 0
                for row in csv_reader:
                    numero_economico = row[1].strip()
                    placa = row[14].strip()
                    modelo = row[10].strip()
                    conductor = row[3].strip() if row[3].strip() else "No Asignado"

                    if not placa or not numero_economico:
                        print(f"Fila omitida por no tener placa o no. económico: {row}")
                        skipped_count += 1
                        continue

                    if Vehiculo.query.filter_by(placa=placa).first() or \
                       Vehiculo.query.filter_by(numero_economico=numero_economico).first():
                        print(f"Unidad '{placa}' / '{numero_economico}' ya existe, omitiendo.")
                        skipped_count += 1
                        continue
                    
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
                    imported_count += 1
                    print(f"Importando: {numero_economico} - {placa}")

                db.session.commit()
                print("\n--- Importación Finalizada ---")
                print(f"Vehículos importados exitosamente: {imported_count}")
                print(f"Vehículos omitidos: {skipped_count}")

        except Exception as e:
            print(f"Ocurrió un error durante la importación: {e}")
            db.session.rollback()

if __name__ == '__main__':
    # La gestión de la base de datos se debe hacer con 'flask db upgrade'
    # No es necesario db.create_all() aquí.
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
