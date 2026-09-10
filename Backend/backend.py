import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_DIR = os.path.join(ROOT_DIR, "DATABASE")

for path in (ROOT_DIR, DATABASE_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import base64
import time
import threading
try:
    import cv2
    import pyzbar.pyzbar as pyzbar
except (ImportError, OSError):
    cv2 = None
    pyzbar = None
import gestion_estudiantes as db


PIXEL_TRANSPARENTE = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

def autenticar_usuario(usuario, password, es_admin):
    usr = db.buscar_usuario_sistema(usuario)
    if usr:
        rol_requerido = "administrador" if es_admin else "docente"
        if usr["rol"] == rol_requerido and usr["password"] == password:
            return True, usr["nombre"]
    return False, None

def validar_y_registrar_manual(id_ingresado):
    if not id_ingresado:
        return "⚠️ Por favor ingrese un ID de estudiante.", "orange"

    if not db.esta_abierto_ahora():
        horario = db.obtener_horario()
        return f"⏰ El registro está cerrado. Horario permitido: {horario['hora_inicio']} a {horario['hora_fin']}", "orange"

    exito, mensaje = db.registrar_asistencia(id_ingresado)
    color = "green" if exito else ("yellow" if "ya registró" in mensaje else "red")
    return mensaje, color

class CamaraManager:
    def __init__(self):
        self.escaneando = False
        self.cap = None

    def detener_camara(self):
        self.escaneando = False
        time.sleep(0.1)
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def iniciar_transmision(self, indice_camara, img_control, txt_estado_control, page):
        self.detener_camara()
        if cv2 is None or pyzbar is None:
            txt_estado_control.value = (
                "❌ El escáner requiere opencv-python y pyzbar. "
                "Instala las dependencias del proyecto."
            )
            txt_estado_control.color = "red"
            page.update()
            return

        idx = int(indice_camara)
        
        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(idx)

        if not self.cap.isOpened():
            txt_estado_control.value = f"❌ No se pudo abrir la cámara {idx}"
            txt_estado_control.color = "red"
            page.update()
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        txt_estado_control.value = f"📷 Cámara {idx} activa. Apunte el código QR."
        txt_estado_control.color = "white"
        self.escaneando = True
        page.update()

        def capturar_loop():
            while self.escaneando:
                try:
                    if self.cap is None or not self.cap.isOpened():
                        break

                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        time.sleep(0.01)
                        continue

                    try:
                        barcodes = pyzbar.decode(frame)
                        for barcode in barcodes:
                            (x, y, w, h) = barcode.rect
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                            codigo_leido = barcode.data.decode("utf-8")

                            exito, msg = db.registrar_asistencia(codigo_leido)
                            txt_estado_control.value = msg
                            txt_estado_control.color = "#4CAF50" if exito else "red"
                    except Exception:
                        pass

                    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    img_base64 = base64.b64encode(buffer).decode("utf-8")

                    img_control.src = img_base64
                    img_control.update()
                    time.sleep(0.033)

                except Exception as e:
                    print(f"Error en transmisión de cámara: {e}")
                    break

        hilo = threading.Thread(target=capturar_loop, daemon=True)
        hilo.start()

def obtener_datos_base_datos():
    datos = db.obtener_reporte_completo_db()
    total_usuarios = len(datos)
    total_estudiantes = sum(1 for u in datos if u["rol"] == "estudiante")
    total_presentes = sum(1 for u in datos if u["asistencia"] == "Presente")
    
    resumen = {
        "total": total_usuarios,
        "estudiantes": total_estudiantes,
        "presentes": total_presentes
    }
    return datos, resumen

def corregir_caracteres(texto: str) -> str:
    if not texto:
        return ""
    
    # Si contiene caracteres problemáticos
    if "?" in texto:
        # Reemplazos específicos comunes según el patrón
        texto = texto.replace("?", "ñ")
        
    return texto
