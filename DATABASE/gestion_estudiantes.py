import calendar
import csv
import hashlib
import hmac
import io
import os
import secrets
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("FOODPASS_DATA_DIR", str(BASE_DIR))).expanduser().resolve()
DB = str(DATA_DIR / "restaurante.db")
CSV_PATH = Path(
    os.environ.get(
        "FOODPASS_STUDENTS_CSV",
        str(BASE_DIR / "DATABASE" / "estudiantes.csv"),
    )
)
HISTORIAL_DIR = DATA_DIR / "historial_reinicios"
DATA_DIR.mkdir(exist_ok=True, parents=True)
HISTORIAL_DIR.mkdir(exist_ok=True, parents=True)
grados_disponibles = ["6A", "6B", "7A", "7B", "8A", "8B", "9A", "9B", "10A", "10B", "11A"]

PASSWORD_HASH_ITERATIONS = 600_000
COLOMBIA_TZ = timezone(timedelta(hours=-5), "COT")


def ahora_colombia():
    return datetime.now(COLOMBIA_TZ).replace(tzinfo=None)


def _hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def _password_hash_matches(password, stored_password):
    try:
        scheme, iterations_text, salt_text, digest_text = stored_password.split("$")
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_text)
        expected = bytes.fromhex(digest_text)
        if scheme != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def verificar_password(password, stored_password):
    if not password or not stored_password:
        return False

    if stored_password.startswith("pbkdf2_sha256$"):
        return _password_hash_matches(password, stored_password)

    if not hmac.compare_digest(password, stored_password):
        return False

    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET password = ? WHERE password = ?",
            (_hash_password(password), stored_password),
        )
        conn.commit()
    return True


def _usuarios_iniciales():
    if os.environ.get("FOODPASS_ENV", "development").strip().lower() != "production":
        return [
            ("admin", "admin123", "Administrador Principal", "administrador"),
            ("3001", "admin123", "Administrador 3001", "administrador"),
            ("docente", "docente123", "Profesor Guía", "docente"),
            ("2001", "docente123", "Profesor 2001", "docente"),
        ]

    admin_usuario = os.environ.get("FOODPASS_ADMIN_USER", "").strip()
    admin_password = os.environ.get("FOODPASS_ADMIN_PASSWORD", "")
    docente_usuario = os.environ.get("FOODPASS_DOCENTE_USER", "").strip()
    docente_password = os.environ.get("FOODPASS_DOCENTE_PASSWORD", "")

    if not all((admin_usuario, admin_password, docente_usuario, docente_password)):
        raise RuntimeError(
            "En producción configura FOODPASS_ADMIN_USER, "
            "FOODPASS_ADMIN_PASSWORD, FOODPASS_DOCENTE_USER y "
            "FOODPASS_DOCENTE_PASSWORD."
        )
    if admin_usuario == docente_usuario:
        raise RuntimeError("El usuario administrador y el docente deben ser distintos.")
    if len(admin_password) < 12 or len(docente_password) < 12:
        raise RuntimeError("Las contraseñas de producción deben tener al menos 12 caracteres.")

    return [
        (admin_usuario, admin_password, "Administrador", "administrador"),
        (docente_usuario, docente_password, "Docente", "docente"),
    ]


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


def importar_estudiantes_csv(contenido):
    if isinstance(contenido, bytes):
        texto = contenido.decode("utf-8-sig")
    else:
        texto = str(contenido)

    muestra = texto[:2048]
    delimitador = ";" if ";" in muestra else ","
    lector = csv.DictReader(io.StringIO(texto, newline=""), delimiter=delimitador)
    encabezados = {
        str(encabezado).replace('"', "").replace("'", "").strip().upper()
        for encabezado in (lector.fieldnames or [])
        if encabezado
    }
    tiene_codigo = "CODIGO" in encabezados or "CÓDIGO" in encabezados
    tiene_tarjeta = encabezados.intersection(
        {"TARJETA", "TARJETA_IDENTIDAD", "DOCUMENTO"}
    )
    if not tiene_codigo or not tiene_tarjeta:
        raise ValueError(
            "El CSV debe incluir las columnas CODIGO y TARJETA_IDENTIDAD (o DOCUMENTO)."
        )

    registrados = 0
    omitidos = 0
    errores = 0

    with get_connection() as conn:
        for fila in lector:
            fila_limpia = {
                str(clave).replace('"', "").replace("'", "").strip().upper():
                (valor or "").strip()
                for clave, valor in fila.items()
                if clave
            }
            codigo = fila_limpia.get("CODIGO") or fila_limpia.get("CÓDIGO")
            tarjeta = (
                fila_limpia.get("TARJETA")
                or fila_limpia.get("TARJETA_IDENTIDAD")
                or fila_limpia.get("DOCUMENTO")
            )
            if not codigo or not tarjeta:
                errores += 1
                continue

            n1 = fila_limpia.get("NOMBRE1", "")
            n2 = fila_limpia.get("NOMBRE2", "")
            nombre = (
                f"{n1} {n2}".strip()
                if n1 or n2
                else fila_limpia.get("NOMBRE", "Sin Nombre")
            )
            a1 = fila_limpia.get("APELLIDO1", "")
            a2 = fila_limpia.get("APELLIDO2", "")
            apellidos = (
                f"{a1} {a2}".strip()
                if a1 or a2
                else fila_limpia.get("APELLIDOS", "Sin Apellido")
            )
            grado = fila_limpia.get("GRADO") or "S/D"

            try:
                conn.execute(
                    """
                    INSERT INTO estudiantes
                        (codigo, tarjeta_identidad, grado, nombre, apellidos)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (codigo, tarjeta, grado, nombre, apellidos),
                )
                registrados += 1
            except sqlite3.IntegrityError as exc:
                if "UNIQUE" in str(exc) or "PRIMARY KEY" in str(exc):
                    omitidos += 1
                else:
                    errores += 1

        conn.commit()

    return {
        "registrados": registrados,
        "omitidos": omitidos,
        "errores": errores,
    }


def crear_tablas():
    usuarios_iniciales = _usuarios_iniciales()
    produccion = os.environ.get("FOODPASS_ENV", "development").strip().lower() == "production"
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

        if produccion:
            usuarios_prueba = {
                "admin": "admin123",
                "3001": "admin123",
                "docente": "docente123",
                "2001": "docente123",
            }
            for usuario, password_prueba in usuarios_prueba.items():
                existente = cursor.execute(
                    "SELECT password FROM usuarios WHERE usuario = ?",
                    (usuario,),
                ).fetchone()
                if existente and (
                    existente["password"] == password_prueba
                    or _password_hash_matches(password_prueba, existente["password"])
                ):
                    cursor.execute("DELETE FROM usuarios WHERE usuario = ?", (usuario,))

        for usr, pwd, nom, rol in usuarios_iniciales:
            existe = cursor.execute(
                "SELECT 1 FROM usuarios WHERE usuario = ?",
                (usr,),
            ).fetchone()
            if not existe:
                cursor.execute(
                    """
                    INSERT INTO usuarios (usuario, password, nombre, rol)
                    VALUES (?, ?, ?, ?)
                    """,
                    (usr, _hash_password(pwd), nom, rol),
                )

        usuarios_legacy = cursor.execute(
            "SELECT usuario, password FROM usuarios"
        ).fetchall()
        for usuario, password in usuarios_legacy:
            if not password.startswith("pbkdf2_sha256$"):
                cursor.execute(
                    "UPDATE usuarios SET password = ? WHERE usuario = ?",
                    (_hash_password(password), usuario),
                )

        conn.commit()

    # Si la tabla está vacía, cargar el CSV inicial configurado.
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM estudiantes")
        if cursor.fetchone()[0] == 0 and CSV_PATH.exists():
            resultado = importar_estudiantes_csv(CSV_PATH.read_bytes())
            if resultado["errores"]:
                print(
                    "La carga inicial del CSV tuvo "
                    f"{resultado['errores']} fila(s) inválida(s)."
                )

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
    ahora = ahora_colombia()
    ahora_min = ahora.hour * 60 + ahora.minute

    if inicio_min is None or fin_min is None:
        return False

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
    fecha_hoy = ahora_colombia().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM asistencias 
            WHERE tarjeta_estudiante = ? AND DATE(fecha_hora) = DATE(?)
        """, (tarjeta, fecha_hoy))

        if cursor.fetchone():
            return False, f"⚠️ {nombre_completo} ya registró asistencia hoy."

        fecha_actual = ahora_colombia().strftime("%Y-%m-%d %H:%M:%S")
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
    fecha_hoy = ahora_colombia().strftime("%Y-%m-%d")
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
    fecha_hoy = ahora_colombia().strftime("%Y-%m-%d")
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


def obtener_historial_estudiante(codigo):
    fecha_hoy = ahora_colombia().date()
    inicio_semana = fecha_hoy - timedelta(days=fecha_hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    inicio_mes = fecha_hoy.replace(day=1)
    ultimo_dia_mes = calendar.monthrange(fecha_hoy.year, fecha_hoy.month)[1]
    fin_mes = fecha_hoy.replace(day=ultimo_dia_mes)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.codigo, e.nombre, e.apellidos, e.tarjeta_identidad,
                   COUNT(a.id) AS total_registros,
                   COALESCE(SUM(CASE WHEN DATE(a.fecha_hora) BETWEEN ? AND ? THEN 1 ELSE 0 END), 0) AS semana,
                   COALESCE(SUM(CASE WHEN DATE(a.fecha_hora) BETWEEN ? AND ? THEN 1 ELSE 0 END), 0) AS mes
            FROM estudiantes e
            LEFT JOIN asistencias a ON e.tarjeta_identidad = a.tarjeta_estudiante
            WHERE e.codigo = ?
            GROUP BY e.codigo, e.nombre, e.apellidos, e.tarjeta_identidad
            """,
            (
                inicio_semana.isoformat(),
                fin_semana.isoformat(),
                inicio_mes.isoformat(),
                fin_mes.isoformat(),
                codigo,
            ),
        )
        fila = cursor.fetchone()
        if not fila:
            return None

        cursor.execute(
            """
            SELECT DATE(a.fecha_hora) AS fecha, COUNT(*) AS cantidad
            FROM estudiantes e
            JOIN asistencias a ON e.tarjeta_identidad = a.tarjeta_estudiante
            WHERE e.codigo = ?
            GROUP BY DATE(a.fecha_hora)
            ORDER BY DATE(a.fecha_hora) DESC
            LIMIT 30
            """,
            (codigo,),
        )
        detalle = [
            {"fecha": row["fecha"], "cantidad": row["cantidad"]}
            for row in cursor.fetchall()
        ]

        return {
            "codigo": fila["codigo"],
            "nombre": f"{fila['nombre']} {fila['apellidos']}".strip(),
            "total_registros": int(fila["total_registros"] or 0),
            "semana": int(fila["semana"] or 0),
            "mes": int(fila["mes"] or 0),
            "detalle": detalle,
        }


def guardar_backup_actual():
    HISTORIAL_DIR.mkdir(exist_ok=True, parents=True)
    timestamp = ahora_colombia()
    fecha = timestamp.date()
    semana = fecha.isocalendar()[1]
    mes_nombre = calendar.month_name[fecha.month]
    mes_dir = HISTORIAL_DIR / str(fecha.year) / f"{fecha.month:02d}_{mes_nombre.lower()}" / f"semana_{semana:02d}"
    mes_dir.mkdir(parents=True, exist_ok=True)

    nombre_backup = f"restaurante_backup_{fecha.isoformat()}_{timestamp.strftime('%H-%M-%S')}.db"
    destino = mes_dir / nombre_backup
    shutil.copy2(DB, destino)

    resumen = {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_calendario": fecha.isoformat(),
        "anio": fecha.year,
        "mes": f"{fecha.month:02d}_{mes_nombre}",
        "semana": f"Semana {semana}",
        "archivo": nombre_backup,
        "total_asistencias": contar_asistencias_hoy(),
        "ruta": str(destino),
        "ruta_persistente": str(destino.relative_to(BASE_DIR)),
    }
    resumen_path = mes_dir / f"restaurante_backup_{fecha.isoformat()}_{timestamp.strftime('%H-%M-%S')}.json"
    with open(resumen_path, "w", encoding="utf-8") as archivo:
        import json
        json.dump(resumen, archivo, ensure_ascii=False, indent=2)

    return {"nombre": nombre_backup, "ruta": str(destino), "resumen": str(resumen_path), "fecha": fecha.isoformat(), "mes": resumen["mes"], "semana": resumen["semana"]}


def contar_asistencias_hoy():
    fecha_hoy = ahora_colombia().strftime("%Y-%m-%d")
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
    for path in sorted(HISTORIAL_DIR.rglob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        resumen = path.with_suffix(".json")
        try:
            fecha_str = datetime.fromtimestamp(
                path.stat().st_mtime, COLOMBIA_TZ
            ).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            fecha_str = path.name

        archivos.append({
            "nombre": path.name,
            "fecha": fecha_str,
            "tamano_kb": round(path.stat().st_size / 1024, 2),
            "ruta": str(path),
            "resumen": str(resumen) if resumen.exists() else None,
        })
    return archivos


def reiniciar_plataforma():
    """
    Guarda las asistencias del día actual en el historial y las borra.
    Mantiene el histórico de los últimos 30 días.
    """
    # Primero guardar el backup del día
    guardar_asistencias_del_dia_automatico()

    # Luego limpiar solo el día actual
    backup = guardar_backup_actual()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM asistencias")
        conn.commit()

    # Limpiar histórico antiguo (más de 30 días)
    eliminados = limpiar_historial_antiguo(30)

    msg = f"Se guardó un nuevo registro en {backup['nombre']} y la plataforma fue reiniciada."
    if eliminados > 0:
        msg += f" Se eliminaron {eliminados} respaldos antiguos (>30 días)."

    return True, msg


def eliminar_registro_historial(nombre_archivo):
    if not nombre_archivo:
        return False, "No se especificó un registro para eliminar."

    if nombre_archivo.startswith(str(HISTORIAL_DIR)):
        base_path = Path(nombre_archivo)
    else:
        base_path = HISTORIAL_DIR / nombre_archivo

    db_path = base_path if base_path.suffix.lower() == ".db" else base_path.with_suffix(".db")
    json_path = base_path if base_path.suffix.lower() == ".json" else base_path.with_suffix(".json")

    eliminados = 0
    for ruta in (db_path, json_path):
        if ruta.exists():
            ruta.unlink()
            eliminados += 1

    if eliminados == 0:
        return False, "No se encontró el registro en el historial."

    return True, f"Se eliminó el registro del historial: {db_path.name}"


def resetear_usuarios():
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        conn.commit()
    crear_tablas()
    print("✅ Usuarios restablecidos con la configuración inicial.")


def guardar_asistencias_del_dia_automatico():
    """
    Guarda automáticamente las asistencias del día en el historial
    sin borrar los datos actuales. Se ejecuta al finalizar el horario.
    """
    fecha_hoy = ahora_colombia().strftime("%Y-%m-%d")

    # Verificar si ya hay asistencias hoy
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM asistencias WHERE DATE(fecha_hora) = DATE(?)", (fecha_hoy,))
        total = cursor.fetchone()[0]

        if total == 0:
            return False, "No hay asistencias para guardar hoy."

    # Crear backup solo del día actual
    timestamp = ahora_colombia().strftime("%Y%m%d_%H%M%S")
    nombre_backup = f"asistencias_{timestamp}.db"
    ruta_backup = HISTORIAL_DIR / nombre_backup

    try:
        # Copiar base de datos completa
        shutil.copy2(DB, ruta_backup)
        return True, f"✅ Asistencias guardadas en {nombre_backup}"
    except Exception as e:
        return False, f"❌ Error al guardar: {str(e)}"


def limpiar_historial_antiguo(dias_limite=30):
    """
    Elimina backups de más de 'dias_limite' días para mantener el histórico limpio.
    """
    fecha_limite = ahora_colombia() - timedelta(days=dias_limite)
    eliminados = 0

    for archivo in HISTORIAL_DIR.glob("asistencias_*.db"):
        try:
            # Extraer fecha del nombre: asistencias_YYYYMMDD_HHMMSS.db
            partes = archivo.stem.split("_")
            if len(partes) >= 2:
                fecha_str = partes[1]  # YYYYMMDD
                fecha_archivo = datetime.strptime(fecha_str, "%Y%m%d")

                if fecha_archivo < fecha_limite:
                    archivo.unlink()
                    eliminados += 1
        except Exception:
            continue

    return eliminados


def verificar_y_archivar_dia_anterior():
    """
    Verifica si hay asistencias de días anteriores y las archiva.
    Esto se ejecuta al inicio del sistema cada día.
    """
    fecha_hoy = ahora_colombia().strftime("%Y-%m-%d")

    with get_connection() as conn:
        cursor = conn.cursor()
        # Buscar asistencias de días anteriores
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM asistencias
            WHERE DATE(fecha_hora) < DATE(?)
        """, (fecha_hoy,))

        total_antiguos = cursor.fetchone()[0]

        if total_antiguos > 0:
            # Guardar backup antes de limpiar
            guardar_asistencias_del_dia_automatico()

            # Eliminar asistencias antiguas (solo mantener el día actual)
            cursor.execute("DELETE FROM asistencias WHERE DATE(fecha_hora) < DATE(?)", (fecha_hoy,))
            conn.commit()

            # Limpiar histórico de más de 30 días
            limpiar_historial_antiguo(30)

            return True, f"✅ Se archivaron {total_antiguos} registros antiguos."

    return False, "No hay registros antiguos para archivar."


if __name__ == "__main__":
    crear_tablas()