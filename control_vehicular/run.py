# run.py
import click
from app import create_app, db
from app.models import User

app = create_app()

@app.cli.command("create-user")
@click.argument("username")
@click.argument("password")
@click.option("--role", default="vigilante", help="Rol del usuario (admin o vigilante)")
def create_user(username, password, role):
    """Crea un nuevo usuario en la base de datos."""
    # --- CORRECCIÓN AQUÍ ---
    # Envolvemos la lógica en app.app_context() para que tenga acceso a la BD.
    with app.app_context():
        # Primero, creamos todas las tablas si no existen.
        db.create_all()

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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
