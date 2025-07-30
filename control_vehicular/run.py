# run.py
import click
import csv
import base64
import qrcode
import io
import uuid
from app import create_app, db, socketio
from app.models import User, Vehiculo, Operador, PosicionEje

app = create_app()

# ... (otros comandos existentes)

@app.cli.command("seed-positions")
def seed_positions():
    """Crea las posiciones estándar de ejes y llantas para tractocamiones."""
    with app.app_context():
        if PosicionEje.query.first():
            print("Las posiciones de llantas ya han sido creadas.")
            return

        posiciones = [
            {'codigo': 'DI', 'descripcion': 'Delantera Izquierda'},
            {'codigo': 'DD', 'descripcion': 'Delantera Derecha'},
            {'codigo': 'T1LI', 'descripcion': 'Eje Trasero 1 - Izquierda Interior'},
            {'codigo': 'T1LE', 'descripcion': 'Eje Trasero 1 - Izquierda Exterior'},
            {'codigo': 'T1RI', 'descripcion': 'Eje Trasero 1 - Derecha Interior'},
            {'codigo': 'T1RE', 'descripcion': 'Eje Trasero 1 - Derecha Exterior'},
            {'codigo': 'T2LI', 'descripcion': 'Eje Trasero 2 - Izquierda Interior'},
            {'codigo': 'T2LE', 'descripcion': 'Eje Trasero 2 - Izquierda Exterior'},
            {'codigo': 'T2RI', 'descripcion': 'Eje Trasero 2 - Derecha Interior'},
            {'codigo': 'T2RE', 'descripcion': 'Eje Trasero 2 - Derecha Exterior'},
        ]
        
        for pos in posiciones:
            nueva_posicion = PosicionEje(codigo=pos['codigo'], descripcion=pos['descripcion'])
            db.session.add(nueva_posicion)
        
        db.session.commit()
        print("Posiciones de llantas para tractocamión creadas exitosamente.")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
