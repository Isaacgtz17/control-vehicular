# scanner.py
import cv2
import requests
import time
from pyzbar import pyzbar

BACKEND_URL = "http://127.0.0.1:5000/verificar_qr"
COOLDOWN_SECONDS = 3

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

last_code_detected = None
last_detection_time = 0

print("\n>>> Escáner iniciado correctamente. Apunta un código a la cámara.")
print(">>> Presiona 'q' en la ventana de la cámara para salir.")

while True:
    success, frame = cap.read()
    if not success:
        time.sleep(0.5)
        continue

    qr_codes = pyzbar.decode(frame)

    for qr in qr_codes:
        qr_data = qr.data.decode('utf-8')
        
        current_time = time.time()
        if qr_data != last_code_detected or (current_time - last_detection_time) > COOLDOWN_SECONDS:
            
            print(f"\n[INFO] Código QR detectado: {qr_data}")
            last_code_detected = qr_data
            last_detection_time = current_time

            try:
                print("[INFO] Verificando con el servidor...")
                response = requests.post(BACKEND_URL, json={'qr_id': qr_data}, timeout=5)
                
                # --- LÓGICA DE RESPUESTA MEJORADA ---
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'autorizado':
                        print("-----------------------------------------")
                        # Imprimimos el mensaje que nos manda el servidor
                        print(f"  {data.get('message', 'ACCIÓN REALIZADA')}")
                        print(f"  Placa: {data.get('placa')}")
                        print(f"  Modelo: {data.get('modelo')}")
                        print("-----------------------------------------")
                    else:
                        # Para otros casos de éxito (200) pero con error lógico
                        print(f"??? RESPUESTA INESPERADA: {data.get('message')} ???")
                elif response.status_code == 404:
                    data = response.json()
                    print("*****************************************")
                    print(f"  ACCESO DENEGADO: {data.get('message')}")
                    print("*****************************************")
                else:
                    print(f"[ERROR] Error del servidor: {response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"[ERROR] No se pudo conectar con el servidor: {e}")

        (x, y, w, h) = qr.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, qr_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow("Escaner de QR", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

print("Cerrando escáner...")
cap.release()
cv2.destroyAllWindows()
