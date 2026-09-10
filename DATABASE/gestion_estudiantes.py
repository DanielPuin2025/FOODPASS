import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB = str(BASE_DIR / "restaurante.db")
CSV_PATH = BASE_DIR / "DATABASE" / "estudiantes.csv"
HISTORIAL_DIR = BASE_DIR / "historial_reinicios"
HISTORIAL_DIR.mkdir(exist_ok=True, parents=True)
grados_disponibles = ["6A", "6B", "7A", "7B", "8A", "8B", "9A", "9B", "10A", "10B", "11A"]


def _normalizar_hora(hora):
    if hora is None:
        return None

    texto = str(hora).strip().lower().replace(" ", "")
    if not texto:
        return None

    meridiano = None
    if texto.endswith("am") or texto.endswith("pm"):
        meridiano = texto[-2:]
        texto = texto[:-2]

    if ":" not in texto:
        return None

    try:
        horas, minutos = texto.split(":", 1)
        horas = int(horas)
        minutos = int(minutos)
    except ValueError:
        return None

    if not (0 <= horas <= 23 and 0 <= minutos <= 59):
        return None

    if meridiano == "pm" and horas < 12:
        horas += 12
    elif meridiano == "am" and horas == 12:
        horas = 0

    return f"{horas:02d}:{minutos:02d}"


def _hora_a_minutos(hora):
    hora_norm = _normalizar_hora(hora)
    if hora_norm is None:
        return None
    h, m = map(int, hora_norm.split(":"))
    return h * 60 + m

def get_connection():
    conn = sqlite3.connect(DB, timeout=10)
    # Forzar que SQLite maneje cadenas en UTF-8
    conn.text_factory = str 
    conn.row_factory = sqlite3.Row
    return conn

def crear_tablas():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Estudiantes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS estudiantes (
                codigo TEXT PRIMARY KEY,
                tarjeta_identidad TEXT UNIQUE NOT NULL,
                grado TEXT NOT NULL,
                nombre TEXT NOT NULL,
                apellidos TEXT NOT NULL
            )
        """)
        # Asistencias
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asistencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarjeta_estudiante TEXT NOT NULL,
                fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tarjeta_estudiante) REFERENCES estudiantes (tarjeta_identidad)
            )
        """)
        # Usuarios (Admins / Docentes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                usuario TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion_horario (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                hora_inicio TEXT NOT NULL,
                hora_fin TEXT NOT NULL
            )
        """)

        cursor.execute(
            "INSERT OR IGNORE INTO configuracion_horario (id, hora_inicio, hora_fin) VALUES (1, '11:30', '12:00')"
        )

        # INSERTAR / ACTUALIZAR USUARIOS DE PRUEBA
        usuarios_iniciales = [
            ('admin', 'admin123', 'Administrador Principal', 'administrador'),
            ('3001', 'admin123', 'Administrador 3001', 'administrador'),
            ('docente', 'docente123', 'Profesor Guía', 'docente'),
            ('2001', 'docente123', 'Profesor 2001', 'docente')
        ]

        for usr, pwd, nom, rol in usuarios_iniciales:
            cursor.execute("""
                INSERT OR REPLACE INTO usuarios (usuario, password, nombre, rol)
                VALUES (?, ?, ?, ?)
            """, (usr, pwd, nom, rol))

        conn.commit()

    # Si la tabla de estudiantes está vacía, cargar el CSV inicial del proyecto.
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM estudiantes")
        if cursor.fetchone()[0] == 0 and CSV_PATH.exists():
            with open(CSV_PATH, mode='r', encoding='utf-8-sig', newline='') as archivo:
                muestra = archivo.read(2048)
                archivo.seek(0)
                delimitador = ';' if ';' in muestra else ','
                lector_csv = csv.DictReader(archivo, delimiter=delimitador)

                for fila in lector_csv:
                    fila_limpia = {
                        str(k).replace('"', '').replace("'", '').strip().upper(): str(v).strip()
                        for k, v in fila.items() if k
                    }

                    codigo = fila_limpia.get('CODIGO') or fila_limpia.get('CÓDIGO')
                    tarjeta = fila_limpia.get('TARJETA') or fila_limpia.get('TARJETA_IDENTIDAD') or fila_limpia.get('DOCUMENTO')
                    grado = fila_limpia.get('GRADO') or 'S/D'

                    n1 = fila_limpia.get('NOMBRE1', '')
                    n2 = fila_limpia.get('NOMBRE2', '')
                    nombre = f"{n1} {n2}".strip() if (n1 or n2) else fila_limpia.get('NOMBRE', 'Sin Nombre')

                    a1 = fila_limpia.get('APELLIDO1', '')
                    a2 = fila_limpia.get('APELLIDO2', '')
                    apellidos = f"{a1} {a2}".strip() if (a1 or a2) else fila_limpia.get('APELLIDOS', 'Sin Apellido')

                    if not codigo or not tarjeta:
                        continue

                    try:
                        conn.execute(
                            """
                            INSERT INTO estudiantes (codigo, tarjeta_identidad, grado, nombre, apellidos)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (codigo, tarjeta, grado, nombre, apellidos),
                        )
                    except sqlite3.IntegrityError:
                        pass

                conn.commit()

# --- CONSULTAS Y REGISTRO ---

def asegurar_horario_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion_horario (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                hora_inicio TEXT NOT NULL,
                hora_fin TEXT NOT NULL
            )
        """)
        cursor.execute(
            "INSERT OR IGNORE INTO configuracion_horario (id, hora_inicio, hora_fin) VALUES (1, '11:30', '12:00')"
        )
        conn.commit()


def obtener_horario():
    asegurar_horario_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT hora_inicio, hora_fin FROM configuracion_horario WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return {"hora_inicio": row["hora_inicio"], "hora_fin": row["hora_fin"]}
    return {"hora_inicio": "11:30", "hora_fin": "12:00"}


def guardar_horario(hora_inicio, hora_fin):
    asegurar_horario_db()
    hora_inicio_norm = _normalizar_hora(hora_inicio)
    hora_fin_norm = _normalizar_hora(hora_fin)

    if hora_inicio_norm is None or hora_fin_norm is None:
        return False, "Formato inválido. Usa HH:MM o HH:MMam/pm."

    inicio_min = _hora_a_minutos(hora_inicio_norm)
    fin_min = _hora_a_minutos(hora_fin_norm)

    if inicio_min is None or fin_min is None:
        return False, "Hora inválida. Usa valores reales de reloj."

    if inicio_min >= fin_min:
        return False, "La apertura debe ser anterior al cierre."

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE configuracion_horario SET hora_inicio = ?, hora_fin = ? WHERE id = 1",
            (hora_inicio_norm, hora_fin_norm),
        )
        conn.commit()

    return True, f"Horario actualizado: {hora_inicio_norm} a {hora_fin_norm}."


def esta_abierto_ahora():
    horario = obtener_horario()
    inicio_min = _hora_a_minutos(horario["hora_inicio"])
    fin_min = _hora_a_minutos(horario["hora_fin"])
    ahora_min = datetime.now().hour * 60 + datetime.now().minute

    if inicio_min is None or fin_min is None:
        return True

    if inicio_min < fin_min:
        return inicio_min <= ahora_min < fin_min

    return ahora_min >= inicio_min or ahora_min < fin_min


def buscar_usuario_sistema(usuario):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
        return cursor.fetchone()

def buscar_estudiante(id_o_tarjeta):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM estudiantes WHERE codigo = ? OR tarjeta_identidad = ?", 
            (id_o_tarjeta, id_o_tarjeta)
        )
        return cursor.fetchone()

def registrar_asistencia(tarjeta_o_codigo):
    if not esta_abierto_ahora():
        horario = obtener_horario()
        return False, f"⏰ Fuera de horario. El registro está habilitado de {horario['hora_inicio']} a {horario['hora_fin']}."

    estudiante = buscar_estudiante(tarjeta_o_codigo)
    if not estudiante:
        return False, "❌ Estudiante no encontrado en el sistema."

    tarjeta = estudiante["tarjeta_identidad"]
    nombre_completo = f"{estudiante['nombre']} {estudiante['apellidos']}"

    # Verificar si ya registró asistencia hoy
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM asistencias 
            WHERE tarjeta_estudiante = ? AND DATE(fecha_hora) = DATE(?)
        """, (tarjeta, fecha_hoy))

        if cursor.fetchone():
            return False, f"⚠️ {nombre_completo} ya registró asistencia hoy."

        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO asistencias (tarjeta_estudiante, fecha_hora)
            VALUES (?, ?)
        """, (tarjeta, fecha_actual))
        conn.commit()

    return True, f"✅ Asistencia registrada: {nombre_completo}"

def agregar_estudiante_db(codigo, nombre, grado, tarjeta=None):
    if not tarjeta:
        tarjeta = codigo  # Por defecto usará el mismo código si no se da tarjeta

    try:
        partes = nombre.strip().split(" ", 1)
        nom = partes[0]
        ape = partes[1] if len(partes) > 1 else ""

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO estudiantes (codigo, tarjeta_identidad, grado, nombre, apellidos)
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, tarjeta, grado, nom, ape))
            conn.commit()
        return True, "🟢 Estudiante registrado exitosamente."
    except sqlite3.IntegrityError:
        return False, "⚠️ El ID o Tarjeta ya existe en el sistema."

def eliminar_estudiante_db(codigo):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM estudiantes WHERE codigo = ?", (codigo,))
        conn.commit()
        if cursor.rowcount > 0:
            return True, "🗑️ Estudiante eliminado con éxito."
        return False, "❌ No se encontró ningún estudiante con ese ID."

def obtener_estudiantes_por_grado(grado):
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.codigo, e.nombre, e.apellidos, e.tarjeta_identidad,
                   CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END AS presente
            FROM estudiantes e
            LEFT JOIN asistencias a 
                   ON e.tarjeta_identidad = a.tarjeta_estudiante 
                  AND DATE(a.fecha_hora) = DATE(?)
            WHERE e.grado = ?
            ORDER BY e.apellidos, e.nombre
        """, (fecha_hoy, grado))
        return cursor.fetchall()

def obtener_reporte_completo_db():
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.codigo, (e.nombre || ' ' || e.apellidos) AS nombre, 'estudiante' AS rol, e.grado,
                   CASE WHEN a.id IS NOT NULL THEN 'Presente' ELSE 'Ausente' END AS asistencia
            FROM estudiantes e
            LEFT JOIN asistencias a 
                   ON e.tarjeta_identidad = a.tarjeta_estudiante 
                  AND DATE(a.fecha_hora) = DATE(?)
            WHERE 1=1
        """, (fecha_hoy,))
        return cursor.fetchall()

def guardar_backup_actual():
    HISTORIAL_DIR.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre_backup = f"restaurante_backup_{timestamp}.db"
    destino = HISTORIAL_DIR / nombre_backup
    shutil.copy2(DB, destino)

    resumen = {
        "timestamp": timestamp,
        "archivo": nombre_backup,
        "total_asistencias": contar_asistencias_hoy(),
        "ruta": str(destino),
    }
    resumen_path = HISTORIAL_DIR / f"restaurante_backup_{timestamp}.json"
    with open(resumen_path, "w", encoding="utf-8") as archivo:
        import json
        json.dump(resumen, archivo, ensure_ascii=False, indent=2)

    return {"nombre": nombre_backup, "ruta": str(destino), "resumen": resumen_path}


def contar_asistencias_hoy():
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM asistencias WHERE DATE(fecha_hora) = DATE(?)",
            (fecha_hoy,),
        )
        return cursor.fetchone()[0]


def listar_historial_reinicios():
    HISTORIAL_DIR.mkdir(exist_ok=True, parents=True)
    archivos = []
    for path in sorted(HISTORIAL_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        archivos.append({
            "nombre": path.name,
            "fecha": datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
            "tamano_kb": round(path.stat().st_size / 1024, 2),
            "ruta": str(path),
        })
    return archivos


def reiniciar_plataforma():
    backup = guardar_backup_actual()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM asistencias")
        conn.commit()
    return True, f"Se guardó el estado previo en {backup['nombre']} y la plataforma fue reiniciada. Todos los estudiantes quedaron en ausente."


def resetear_usuarios():
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        conn.commit()
    crear_tablas()
    print("✅ Usuarios restablecidos con éxito: admin/admin123 y docente/docente123")


if __name__ == "__main__":
    crear_tablas()