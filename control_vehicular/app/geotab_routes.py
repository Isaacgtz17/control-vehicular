# app/geotab_routes.py
from flask import Blueprint, render_template, jsonify, current_app
from flask_login import login_required
from .utils import admin_required
import mygeotab
from datetime import datetime
import pytz

geotab_bp = Blueprint('geotab', __name__, url_prefix='/geotab')

# --- CONFIGURACIÓN DE LA API DE GEOTAB ---
# DEBES RELLENAR ESTAS VARIABLES CON TUS CREDENCIALES
GEOTAB_USERNAME = "centro.monitoreo@gruasmoviles.mx"
GEOTAB_PASSWORD = "Ocmetsodvgaids"
GEOTAB_DATABASE = "gruasmovilesgolfo"

def get_geotab_api():
    """Inicializa y devuelve una instancia de la API de Geotab."""
    try:
        api = mygeotab.API(username=GEOTAB_USERNAME, password=GEOTAB_PASSWORD, database=GEOTAB_DATABASE)
        api.authenticate()
        return api
    except Exception as e:
        print(f"Error al autenticar con Geotab: {e}")
        return None

@geotab_bp.route('/monitoring')
@login_required
@admin_required
def dashboard():
    """Renderiza la página principal del dashboard de monitoreo."""
    return render_template('geotab_dashboard.html')

@geotab_bp.route('/api/fleet_status')
@login_required
@admin_required
def get_fleet_status():
    """
    Endpoint de la API que obtiene y procesa los datos de la flota desde Geotab.
    Implementa las llamadas específicas para odómetro y combustible como se solicitó.
    """
    api = get_geotab_api()
    if not api:
        return jsonify({"error": "No se pudo conectar a la API de Geotab"}), 500

    try:
        # 1. Obtener todos los dispositivos (vehículos)
        devices = api.get("Device")
        device_map = {device['id']: device for device in devices}

        # 2. Obtener la información de estado general (velocidad, ubicación)
        device_status_info = api.get("DeviceStatusInfo")
        
        fleet_data = []
        
        local_tz = pytz.timezone("America/Mexico_City") # Ajusta a tu zona horaria local

        for status in device_status_info:
            device_id = status.get('device', {}).get('id')
            if device_id in device_map:
                device_info = device_map[device_id]
                
                # Convertir fecha a zona horaria local
                utc_date = status.get('dateTime', datetime.utcnow())
                local_date = utc_date.replace(tzinfo=pytz.utc).astimezone(local_tz)

                vehicle_data = {
                    "id": device_id,
                    "name": device_info.get('name'),
                    "is_driving": status.get('isDriving'),
                    "speed": status.get('speed'),
                    "latitude": status.get('latitude'),
                    "longitude": status.get('longitude'),
                    "last_report": local_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "odometer": "N/A",
                    "fuel_level": "N/A"
                }

                # 3. Peticiones "a la carta" para odómetro y combustible (requisito crucial)
                try:
                    # Odómetro
                    odometer_data = api.get("StatusData", 
                                            deviceSearch={"id": device_id}, 
                                            diagnosticSearch={"id": "DiagnosticOdometerId"}, 
                                            resultsLimit=1)
                    if odometer_data:
                        vehicle_data["odometer"] = round(odometer_data[0].get('data', 0), 2)

                    # Nivel de Gasolina
                    fuel_data = api.get("StatusData", 
                                        deviceSearch={"id": device_id}, 
                                        diagnosticSearch={"id": "DiagnosticFuelLevelId"}, 
                                        resultsLimit=1)
                    if fuel_data:
                        vehicle_data["fuel_level"] = round(fuel_data[0].get('data', 0), 2)
                
                except Exception as e:
                    print(f"Error obteniendo datos de diagnóstico para {device_info.get('name')}: {e}")

                fleet_data.append(vehicle_data)

        return jsonify(sorted(fleet_data, key=lambda x: x['name']))

    except Exception as e:
        print(f"Error general en la API de Geotab: {e}")
        return jsonify({"error": "Ocurrió un error al obtener los datos de la flota"}), 500
