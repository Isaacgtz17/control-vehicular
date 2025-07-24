# run.py
# Este archivo es el punto de entrada para ejecutar la aplicación.

from app import create_app, db

# Creamos la instancia de la aplicación llamando a nuestra factory function
app = create_app()

# Este bloque se asegura de que el script se ejecute solo cuando lo llamas directamente
if __name__ == '__main__':
    # Usamos app.app_context() para asegurarnos de que la aplicación
    # esté configurada correctamente antes de intentar crear las tablas de la base de datos.
    with app.app_context():
        db.create_all() # Crea las tablas de la base de datos si no existen
    
    # Ejecuta la aplicación.
    # host='0.0.0.0' permite que sea accesible desde otros dispositivos en la misma red.
    app.run(debug=True, host='0.0.0.0', port=5000)
