# scanner.py
import cv2
import requests
import time
from pyzbar import pyzbar

# --- Configuración ---
BACKEND_URL = "http://127.0.0.1:5000/verificar_qr"
# Nuevo: Tiempo en segundos que un QR debe estar fuera de cámara para ser escaneado de nuevo.
RESET_TIMEOUT_SECONDS = 30 

def find_camera():
    print("[DIAGNÓSTICO] Buscando cámaras disponibles...")
    for index in [0, 1, -1]:
        print(f"[DIAGNÓSTICO] Intentando abrir cámara con índice: {index}")
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            print(f"[ÉXITO] Cámara encontrada y abierta en el índice {index}.")
            return cap
    return None

print(">>> Iniciando escáner de QR...")
cap = find_camera()

if not cap:
    print("ERROR CRÍTICO: No se pudo encontrar una cámara.")
    input("Presiona Enter para salir.")
    exit()

# --- Nueva Lógica: Diccionario para rastrear códigos ---
# Almacenará los códigos que ya fueron procesados y la última vez que fueron vistos.
# Formato: {'contenido_del_qr': tiempo_ultima_vez_visto}
processed_codes = {}

print("\n>>> Escáner iniciado correctamente. Apunta un código a la cámara.")
print(">>> Presiona 'q' en la ventana de la cámara para salir.")

while True:
    success, frame = cap.read()
    if not success:
        time.sleep(0.5)
        continue

    qr_codes_in_frame = pyzbar.decode(frame)
    
    # Creamos un set con los datos de los QR que están visibles AHORA MISMO.
    visible_qr_data = {qr.data.decode('utf-8') for qr in qr_codes_in_frame}

    # 1. Procesar códigos nuevos o que ya no estaban en la lista de procesados.
    for qr in qr_codes_in_frame:
        qr_data = qr.data.decode('utf-8')

        if qr_data not in processed_codes:
            print(f"\n[INFO] Nuevo código QR detectado: {qr_data}")
            
            try:
                print("[INFO] Verificando con el servidor...")
                response = requests.post(BACKEND_URL, json={'qr_id': qr_data}, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'autorizado':
                        print("-----------------------------------------")
                        print(f"  {data.get('message', 'ACCIÓN REALIZADA')}")
                        print(f"  Placa: {data.get('placa')}")
                        print(f"  Modelo: {data.get('modelo')}")
                        print("-----------------------------------------")
                elif response.status_code == 404:
                    data = response.json()
                    print("*****************************************")
                    print(f"  ACCESO DENEGADO: {data.get('message')}")
                    print("*****************************************")
                else:
                    print(f"[ERROR] Error del servidor: {response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] No se pudo conectar con el servidor: {e}")
            
            # Añadimos el código a la lista de procesados con el tiempo actual.
            processed_codes[qr_data] = time.time()
    
    # 2. Actualizar el tiempo de los códigos que siguen visibles.
    for qr_data in visible_qr_data:
        if qr_data in processed_codes:
            processed_codes[qr_data] = time.time()

    # 3. Limpiar códigos que ya no están visibles por más del tiempo de espera.
    codes_to_reset = []
    for qr_data, last_seen in processed_codes.items():
        if qr_data not in visible_qr_data: # Si el código ya no está en la cámara...
            if time.time() - last_seen > RESET_TIMEOUT_SECONDS: # ...y ha pasado el tiempo de espera...
                codes_to_reset.append(qr_data) # ...lo marcamos para resetear.

    for qr_data in codes_to_reset:
        del processed_codes[qr_data]
        print(f"[INFO] Código {qr_data[:8]}... reseteado. Puede ser escaneado de nuevo.")

    # Dibujar los rectángulos en la imagen (esto no cambia)
    for qr in qr_codes_in_frame:
        (x, y, w, h) = qr.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        qr_data = qr.data.decode('utf-8')
        cv2.putText(frame, qr_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow("Escaner de QR", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

print("Cerrando escáner...")
cap.release()
cv2.destroyAllWindows()
