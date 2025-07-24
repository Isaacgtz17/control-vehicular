# scanner.py - Lector de Códigos QR con la Cámara (Versión con diagnóstico)
import cv2
import requests
import time
from pyzbar import pyzbar

# --- Configuración ---
BACKEND_URL = "http://127.0.0.1:5000/verificar_qr"
COOLDOWN_SECONDS = 3

def find_camera():
    """Intenta encontrar y abrir una cámara disponible."""
    print("[DIAGNÓSTICO] Buscando cámaras disponibles...")
    # Intentamos con los índices de cámara más comunes: 0, 1, -1
    for index in [0, 1, -1]:
        print(f"[DIAGNÓSTICO] Intentando abrir cámara con índice: {index}")
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            print(f"[ÉXITO] Cámara encontrada y abierta en el índice {index}.")
            return cap
    return None

# --- Inicialización ---
print(">>> Iniciando escáner de QR...")
cap = find_camera()

if not cap:
    print("*****************************************************")
    print("  ERROR CRÍTICO: No se pudo encontrar una cámara.")
    print("  Asegúrate de que la cámara esté conectada y no")
    print("  esté siendo usada por otro programa (Zoom, Skype, etc).")
    print("*****************************************************")
    input("Presiona Enter para salir.") # Pausa para que el usuario pueda leer el error
    exit()

# Variable para guardar el último código detectado y el tiempo de detección
last_code_detected = None
last_detection_time = 0

print("\n>>> Escáner iniciado correctamente. Apunta un código a la cámara.")
print(">>> Presiona 'q' en la ventana de la cámara para salir.")

# --- Bucle Principal ---
while True:
    # Leemos un frame (una imagen) de la cámara
    success, frame = cap.read()
    if not success:
        print("[ADVERTENCIA] No se pudo leer el frame de la cámara. Intentando de nuevo...")
        time.sleep(0.5)
        continue

    # Usamos pyzbar para buscar códigos QR en la imagen
    qr_codes = pyzbar.decode(frame)

    # Procesamos cada código QR encontrado
    for qr in qr_codes:
        # --- NUEVO CÓDIGO DE DIAGNÓSTICO ---
        print(f"[DEBUG] Objeto QR encontrado: {qr}")
        print(f"[DEBUG] Datos crudos (bytes): {qr.data}")
        # --- FIN DEL CÓDIGO DE DIAGNÓSTICO ---
        
        qr_data = qr.data.decode('utf-8')
        
        current_time = time.time()
        if qr_data != last_code_detected or (current_time - last_detection_time) > COOLDOWN_SECONDS:
            
            print(f"\n[INFO] Código QR detectado: {qr_data}")
            last_code_detected = qr_data
            last_detection_time = current_time

            try:
                print("[INFO] Verificando con el servidor...")
                response = requests.post(BACKEND_URL, json={'qr_id': qr_data}, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data['status'] == 'autorizado':
                        print("-----------------------------------------")
                        print("  ACCESO AUTORIZADO")
                        print(f"  Placa: {data['placa']}")
                        print(f"  Modelo: {data['modelo']}")
                        print(f"  Conductor: {data['conductor']}")
                        print("-----------------------------------------")
                elif response.status_code == 404:
                    data = response.json()
                    print("*****************************************")
                    print(f"  ACCESO DENEGADO: {data['message']}")
                    print("*****************************************")
                else:
                    print(f"[ERROR] Error del servidor: {response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] No se pudo conectar con el servidor: {e}")

        (x, y, w, h) = qr.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, qr_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Mostramos la ventana con la vista de la cámara
    cv2.imshow("Escaner de QR", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# --- Limpieza ---
print("Cerrando escáner...")
cap.release()
cv2.destroyAllWindows()
