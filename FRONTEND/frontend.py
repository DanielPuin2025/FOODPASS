import asyncio
import base64
import csv
import io
import json
import os
import sqlite3
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "FRONTEND")
DATABASE_DIR = os.path.join(ROOT_DIR, "DATABASE")
SYNC_QUEUE_PATH = Path(ROOT_DIR) / "sync_pendiente.json"
SYNC_LOG_PATH = Path(ROOT_DIR) / "sync_log.json"
LOGO_PATH = os.path.abspath(os.path.join(FRONTEND_DIR, "logo.png"))
LOGO_BYTES = (
    open(LOGO_PATH, "rb").read() if os.path.exists(LOGO_PATH) else None
)
LOGO_SENA_PATH = os.path.abspath(os.path.join(FRONTEND_DIR, "logo_sena_ok.png"))
LOGO_SENA_BYTES = (
    open(LOGO_SENA_PATH, "rb").read() if os.path.exists(LOGO_SENA_PATH) else None
)
IMAGEN_RESTAURANTE_PATH = os.path.abspath(os.path.join(FRONTEND_DIR, "imagen_restaurante.png"))
IMAGEN_RESTAURANTE_BYTES = (
    open(IMAGEN_RESTAURANTE_PATH, "rb").read() if os.path.exists(IMAGEN_RESTAURANTE_PATH) else None
)

for path in (ROOT_DIR, DATABASE_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import flet as ft
import gestion_estudiantes as db
import Backend.backend as bk


def leer_cola_sincronizacion():
    if not SYNC_QUEUE_PATH.exists():
        return []
    try:
        with open(SYNC_QUEUE_PATH, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
            return datos if isinstance(datos, list) else []
    except Exception:
        return []


def guardar_cambio_pendiente(tipo, detalle=None):
    cola = leer_cola_sincronizacion()
    cola.append(
        {
            "tipo": tipo,
            "detalle": detalle or {},
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    with open(SYNC_QUEUE_PATH, "w", encoding="utf-8") as archivo:
        json.dump(cola, archivo, ensure_ascii=False, indent=2)
    return True


def sincronizar_cola_local():
    cola = leer_cola_sincronizacion()
    if not cola:
        return []

    for item in cola:
        tipo = item.get("tipo")
        detalle = item.get("detalle", {})
        try:
            if tipo == "marcar_asistencia":
                db.registrar_asistencia(detalle.get("tarjeta_o_codigo"))
            elif tipo == "agregar_estudiante":
                db.agregar_estudiante_db(
                    detalle.get("codigo"),
                    detalle.get("nombre", ""),
                    detalle.get("grado"),
                    detalle.get("tarjeta"),
                )
            elif tipo == "eliminar_estudiante":
                db.eliminar_estudiante_db(detalle.get("codigo"))
            elif tipo == "guardar_horario":
                db.guardar_horario(detalle.get("hora_inicio"), detalle.get("hora_fin"))
            elif tipo == "reiniciar_plataforma":
                db.reiniciar_plataforma()
        except Exception:
            pass

    with open(SYNC_QUEUE_PATH, "w", encoding="utf-8") as archivo:
        json.dump([], archivo, ensure_ascii=False, indent=2)
    return cola


def comprobar_internet():
    try:
        with urllib.request.urlopen("https://www.gstatic.com/generate_204", timeout=5):
            return True
    except Exception:
        return False


def construir_barra_estado_conexion(page):
    if not hasattr(page, "_estado_conexion"):
        page._estado_conexion = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Text("●", size=16, weight=ft.FontWeight.BOLD, color="white"),
                        width=16,
                        height=16,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Text(
                        "ONLINE - Conectado",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                    ),
                ],
                spacing=6,
                alignment=ft.MainAxisAlignment.START,
            ),
            bgcolor="#2E7D32",
            border_radius=8,
            padding=8,
            shadow=ft.BoxShadow(blur_radius=8, color="#00000022"),
            margin=ft.Margin(left=12, top=12, right=0, bottom=0),
            alignment=ft.Alignment(-1, -1),
        )
    return page._estado_conexion


def actualizar_barra_estado_conexion(page, online: bool):
    barra = construir_barra_estado_conexion(page)
    texto = "ONLINE - Conectado" if online else "Modo sin conexión"
    color = "#2E7D32" if online else "#D32F2F"
    barra.bgcolor = color
    barra.content.controls[0].content.value = "●"
    barra.content.controls[0].content.color = "white"
    barra.content.controls[1].value = texto
    barra.content.controls[1].color = "white"
    page._app_state["online"] = online

    if hasattr(page, "update"):
        try:
            page.update()
        except Exception:
            pass


async def vigilar_conexion(page):
    while True:
        online = comprobar_internet() if not getattr(page, "web", False) else True
        if getattr(page, "web", False):
            try:
                online = page.run_javascript("navigator.onLine")
            except Exception:
                online = True
        ultimo_estado = page._app_state.get("online", online)
        if online and not ultimo_estado:
            cambios = sincronizar_cola_local()
            if cambios:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Se sincronizaron {len(cambios)} cambios cuando volvió la conexión."),
                    bgcolor="#2A4B1A",
                )
                page.snack_bar.open = True
        actualizar_barra_estado_conexion(page, online)
        await asyncio.sleep(5)


def main(page: ft.Page):
    # Inicializar las tablas SQLite en caso de que no existan
    db.crear_tablas()

    # Verificar y archivar registros del día anterior automáticamente
    try:
        db.verificar_y_archivar_dia_anterior()
    except Exception as e:
        print(f"Error al verificar archivado automático: {e}")

    if not hasattr(page, "_app_state"):
        page._app_state = {}
    page._app_state.setdefault("online", True)
    asyncio.create_task(vigilar_conexion(page))

    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    camara_mgr = bk.CamaraManager()

    async def descargar_en_navegador(nombre_archivo, contenido_bytes):
        try:
            ruta_guardada = await file_picker.save_file(
                dialog_title="Guardar archivo",
                file_name=nombre_archivo,
                src_bytes=contenido_bytes,
            )
            if ruta_guardada is None and not page.web:
                return

            page.snack_bar = ft.SnackBar(
                ft.Text(f"Descarga iniciada: {nombre_archivo}"),
                bgcolor="#2A4B1A",
            )
            page.snack_bar.open = True
            page.update()
        except Exception as exc:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"No se pudo descargar el archivo: {exc}"),
                bgcolor="#D32F2F",
            )
            page.snack_bar.open = True
            page.update()

    async def exportar_backup_csv(ruta_origen, nombre_backup):
        nombre_salida = os.path.splitext(nombre_backup)[0] + ".csv"
        try:
            conn = sqlite3.connect(ruta_origen)
            try:
                tablas = ["estudiantes", "asistencias"]
                output = io.StringIO(newline="")
                writer = None

                for nombre_hoja in tablas:
                    try:
                        filas = conn.execute(f"SELECT * FROM {nombre_hoja}").fetchall()
                    except sqlite3.DatabaseError:
                        continue

                    columnas = [descripcion[0] for descripcion in conn.execute(f"PRAGMA table_info({nombre_hoja})").fetchall()]
                    if writer is None:
                        writer = csv.writer(output)
                    writer.writerow([])
                    writer.writerow([f"TABLA: {nombre_hoja}"])
                    writer.writerow(columnas)
                    for fila in filas:
                        writer.writerow(list(fila))

                contenido = output.getvalue().encode("utf-8-sig")
                await descargar_en_navegador(nombre_salida, contenido)
            finally:
                conn.close()
        except Exception as exc:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"No se pudo exportar a CSV: {exc}"),
                bgcolor="#D32F2F",
            )
            page.snack_bar.open = True
            page.update()

    def descargar_archivo(ruta_archivo, nombre_archivo, extension="db"):
        if extension.lower() == "csv":
            page.run_task(exportar_backup_csv, ruta_archivo, nombre_archivo)
            return

        try:
            with open(ruta_archivo, "rb") as archivo:
                contenido = archivo.read()
            nombre_descarga = (
                nombre_archivo
                if nombre_archivo.endswith(f".{extension}")
                else f"{nombre_archivo}.{extension}"
            )
            page.run_task(
                descargar_en_navegador,
                nombre_descarga,
                contenido,
            )
        except Exception as exc:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"No se pudo descargar: {exc}"),
                bgcolor="#D32F2F",
            )
            page.snack_bar.open = True
            page.update()

    # --- CONFIGURACIÓN DE TEMA Y ESTILO FOODPASS ---
    page.title = "FoodPass - Sistema de Control de Asistencia"
    page.bgcolor = "#F2F4ED"  # Fondo claro y limpio
    page.padding = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.vertical_alignment = ft.MainAxisAlignment.START
    es_admin = False

    # Colores corporativos basados en el logo
    COLOR_VERDE_LOGICO = "#8CB83E"
    COLOR_VERDE_OSCURO = "#2A4B1A"
    COLOR_AMARILLO_LOGO = "#F0AB00"
    COLOR_BLANCO = "#FFFFFF"

    def limpiar_credenciales():
        input_id.value = ""
        input_pass.value = ""
        lbl_mensaje.value = ""

    def mostrar_vista(contenido):
        barra_estado = construir_barra_estado_conexion(page)
        ultimo_online = bool(page._app_state.get("online", True))
        actualizar_barra_estado_conexion(page, ultimo_online)
        vista = ft.Column(
            controls=[barra_estado, contenido],
            expand=True,
            spacing=0,
        )
        page.clean()
        page.add(
            ft.Container(
                content=vista,
                bgcolor="#F2F4ED",
                expand=True,
            )
        )
        page.update()

    # Componente reutilizable del Logo
    def crear_logo(width=180):
        src_logo = LOGO_BYTES if LOGO_BYTES is not None else "logo.png"
        controles = []
        if LOGO_SENA_BYTES is not None:
            controles.append(
                ft.Image(
                    src=LOGO_SENA_BYTES,
                    width=50,
                    height=40,
                    fit="contain",
                )
            )
        controles.append(
            ft.Image(
                src=src_logo,
                width=width,
                fit="contain",
                error_content=ft.Text(
                    "FOODPASS",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_VERDE_LOGICO,
                ),
            )
        )
        return ft.Row(
            controls=controles,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

    # -------------------------------------------------------------------------
    # VISTA: BASE DE DATOS COMPLETA (SOLO ADMINISTRADOR)
    # -------------------------------------------------------------------------
    def abrir_vista_base_datos(nombre_admin):
        datos, resumen = bk.obtener_datos_base_datos()

        tabla = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Text(
                        "ID/Código", weight=ft.FontWeight.BOLD, color="black"
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Nombre", weight=ft.FontWeight.BOLD, color="black"
                    )
                ),
                ft.DataColumn(
                    ft.Text("Rol", weight=ft.FontWeight.BOLD, color="black")
                ),
                ft.DataColumn(
                    ft.Text("Grado", weight=ft.FontWeight.BOLD, color="black")
                ),
                ft.DataColumn(
                    ft.Text(
                        "Estado Asistencia",
                        weight=ft.FontWeight.BOLD,
                        color="black",
                    )
                ),
            ],
            rows=[],
        )

        total_estudiantes = max(1, resumen["estudiantes"])
        porcentaje_presentes = round((resumen["presentes"] / total_estudiantes) * 100, 1) if total_estudiantes else 0
        porcentaje_ausentes = round(100 - porcentaje_presentes, 1)

        grafico_asistencia = ft.Column(
            controls=[
                ft.Text(
                    "Asistencia del día",
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_VERDE_OSCURO,
                ),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                width=380 * (porcentaje_presentes / 100),
                                height=18,
                                bgcolor=COLOR_VERDE_LOGICO,
                                border_radius=9,
                            ),
                            ft.Container(
                                width=380 * (porcentaje_ausentes / 100),
                                height=18,
                                bgcolor="#E53935",
                                border_radius=9,
                            ),
                        ],
                        spacing=0,
                    ),
                    width=380,
                    height=18,
                    bgcolor="#E5E7EB",
                    border_radius=9,
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            f"Presentes: {porcentaje_presentes}%",
                            color=COLOR_VERDE_OSCURO,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            f"Ausentes: {porcentaje_ausentes}%",
                            color="#E53935",
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=20,
                ),
            ],
            spacing=8,
        )

        historial_input = ft.TextField(
            label="Buscar estudiante por ID",
            hint_text="Ej.: 1001",
            width=260,
            border_color="#D1D5DB",
            color="black",
        )

        historial_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Seguimiento del estudiante",
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    ft.Text(
                        "Ingrese un ID para ver su historial semanal y mensual.",
                        color="black",
                        size=12,
                    ),
                ],
                spacing=8,
            ),
            bgcolor="#F8F9FA",
            border=ft.Border.all(1, "#D1D5DB"),
            border_radius=8,
            padding=12,
        )

        def abrir_historial_estudiante(e):
            codigo = (historial_input.value or "").strip()

            if not codigo:
                historial_panel.content = ft.Column(
                    controls=[
                        ft.Text(
                            "Seguimiento del estudiante",
                            weight=ft.FontWeight.BOLD,
                            color=COLOR_VERDE_OSCURO,
                        ),
                        ft.Text(
                            "Ingrese un ID para consultar el historial del estudiante.",
                            color="#E53935",
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=8,
                )
                page.update()
                return

            info = db.obtener_historial_estudiante(codigo)
            if not info:
                historial_panel.content = ft.Column(
                    controls=[
                        ft.Text(
                            "Seguimiento del estudiante",
                            weight=ft.FontWeight.BOLD,
                            color=COLOR_VERDE_OSCURO,
                        ),
                        ft.Text(
                            f"No se encontró un estudiante con el ID {codigo}.",
                            color="#E53935",
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    spacing=8,
                )
                page.update()
                return

            detalle = ft.Column(
                controls=[
                    ft.Text(
                        f"Estudiante: {info['nombre']} ({info['codigo']})",
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    ft.Text(f"Entradas esta semana: {info['semana']}"),
                    ft.Text(f"Entradas este mes: {info['mes']}"),
                    ft.Text(f"Total de registros: {info['total_registros']}"),
                    ft.Divider(),
                    ft.Text(
                        "Detalle por día:",
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                ],
                spacing=8,
            )

            if info["detalle"]:
                for item in info["detalle"]:
                    detalle.controls.append(
                        ft.Text(
                            f"• {item['fecha']}: {item['cantidad']} ingreso(s)",
                            color="black",
                        )
                    )
            else:
                detalle.controls.append(
                    ft.Text(
                        "Este estudiante no tiene registros de asistencia.",
                        color="black",
                    )
                )

            historial_panel.content = detalle
            page.update()

        for u in datos:
            color_asistencia = (
                COLOR_VERDE_LOGICO
                if u["asistencia"] == "Presente"
                else "#E53935"
            )

        for u in datos:
            color_asistencia = (
                COLOR_VERDE_LOGICO
                if u["asistencia"] == "Presente"
                else "#E53935"
            )

            tabla.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(u["codigo"], color="black")),
                        ft.DataCell(ft.Text(u["nombre"], color="black")),
                        ft.DataCell(
                            ft.Text(u["rol"].capitalize(), color="black")
                        ),
                        ft.DataCell(ft.Text(u["grado"], color="black")),
                        ft.DataCell(
                            ft.Text(
                                u["asistencia"],
                                color=color_asistencia,
                                weight=ft.FontWeight.BOLD,
                            )
                        ),
                    ]
                )
            )

        def volver_al_admin(e):
            mostrar_vista(
                ft.Container(
                    content=construir_panel_admin(nombre_admin),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                )
            )

        layout_bd = ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(140),
                    ft.Text(
                        "BASE DE DATOS DEL SISTEMA",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    ft.Text(
                        f"Total Registros: {resumen['total']} | Estudiantes: {resumen['estudiantes']} | Presentes Hoy: {resumen['presentes']}",
                        size=13,
                        color="black",
                    ),
                    grafico_asistencia,
                    ft.Row(
                        controls=[
                            historial_input,
                            ft.Button(
                                "Seguimiento",
                                on_click=abrir_historial_estudiante,
                                bgcolor=COLOR_AMARILLO_LOGO,
                                color="white",
                            ),
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    historial_panel,
                    ft.Divider(color=COLOR_VERDE_LOGICO),
                    ft.Container(
                        content=ft.Column(
                            controls=[tabla], scroll=ft.ScrollMode.ALWAYS
                        ),
                        height=340,
                        border=ft.Border.all(1, "#D1D5DB"),
                        border_radius=8,
                        padding=10,
                    ),
                    ft.Container(height=10),
                    ft.Button(
                        "🔙 Volver al Panel Admin",
                        on_click=volver_al_admin,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=COLOR_BLANCO,
            width=680,
            padding=25,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000"),
        )

        mostrar_vista(
            ft.Container(
                content=layout_bd, alignment=ft.Alignment(0, 0), expand=True
            )
        )

    # -------------------------------------------------------------------------
    # VISTA: ESTUDIANTES POR GRADO
    # -------------------------------------------------------------------------
    def abrir_vista_grados(nombre_docente, grado_seleccionado):
        lista_estudiantes = ft.ListView(
            expand=True, spacing=8, padding=10, auto_scroll=False
        )

        def recargar_lista():
            lista_estudiantes.controls.clear()
            estudiantes = db.obtener_estudiantes_por_grado(grado_seleccionado)

            for est in estudiantes:
                cod = est["codigo"]
                est_nombre = f"{est['nombre']} {est['apellidos']}"
                esta_presente = bool(est["presente"])

                estado = "✅ Presente" if esta_presente else "❌ Ausente"
                color_estado = (
                    COLOR_VERDE_LOGICO if esta_presente else "#E53935"
                )

                def marcar_asistencia(e, tarjeta=est["tarjeta_identidad"]):
                    if not page._app_state.get("online", True):
                        guardar_cambio_pendiente("marcar_asistencia", {"tarjeta_o_codigo": tarjeta})
                        page.snack_bar = ft.SnackBar(
                            ft.Text("Sin conexión: el registro quedó pendiente y se aplicará al volver online."),
                            bgcolor="#D32F2F",
                        )
                        page.snack_bar.open = True
                    db.registrar_asistencia(tarjeta)
                    recargar_lista()
                    page.update()

                acciones = [
                    ft.Text(
                        estado, color=color_estado, weight=ft.FontWeight.BOLD
                    )
                ]

                if not esta_presente:
                    btn_confirmar = ft.Button(
                        "Confirmar",
                        on_click=marcar_asistencia,
                        bgcolor=COLOR_VERDE_LOGICO,
                        color="white",
                        height=30,
                        style=ft.ButtonStyle(padding=5),
                    )
                    acciones.append(btn_confirmar)

                tarjeta_ui = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(
                                f"ID: {cod}",
                                weight=ft.FontWeight.BOLD,
                                width=70,
                                color="black",
                            ),
                            ft.Text(f"{est_nombre}", expand=True, color="black"),
                            ft.Row(controls=acciones, spacing=10),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    bgcolor="#F8F9FA",
                    padding=10,
                    border_radius=8,
                    border=ft.Border.all(1, "#E5E7EB"),
                )
                lista_estudiantes.controls.append(tarjeta_ui)

            if not estudiantes:
                lista_estudiantes.controls.append(
                    ft.Text(
                        "No hay estudiantes registrados en este grado.",
                        color="#E53935",
                    )
                )
            page.update()

        recargar_lista()

        def volver_al_panel(e):
            mostrar_vista(
                ft.Container(
                    content=construir_panel_docente(nombre_docente),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                )
            )

        layout_grados = ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(130),
                    ft.Text(
                        f"LISTADO - {grado_seleccionado.upper()}",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    ft.Divider(color=COLOR_VERDE_LOGICO),
                    ft.Container(
                        content=lista_estudiantes,
                        height=320,
                        border=ft.Border.all(1, "#D1D5DB"),
                        border_radius=8,
                        padding=5,
                    ),
                    ft.Container(height=10),
                    ft.Button(
                        "🔙 Volver al Panel Docente",
                        on_click=volver_al_panel,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=COLOR_BLANCO,
            width=540,
            padding=25,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000"),
        )

        mostrar_vista(
            ft.Container(
                content=layout_grados, alignment=ft.Alignment(0, 0), expand=True
            )
        )

    # -------------------------------------------------------------------------
    # VISTA: PANEL DEL ADMINISTRADOR
    # -------------------------------------------------------------------------
    def mostrar_registro_backup(item, volver_callback=None, nombre_sesion=None):
        ruta_json = item.get("resumen")
        contenido = "No hay detalle disponible para este registro."
        if ruta_json and os.path.exists(ruta_json):
            try:
                with open(ruta_json, "r", encoding="utf-8") as archivo:
                    contenido = archivo.read()
            except Exception:
                contenido = "No se pudo leer el detalle del registro."

        def volver_al_historial(e):
            if callable(volver_callback):
                volver_callback(e)
            else:
                page.update()

        def cargar_asistencia_backup(ruta_db):
            presentes = []
            ausentes = []
            if os.path.exists(ruta_db):
                try:
                    fecha_ref = None
                    nombre_archivo = os.path.basename(ruta_db)
                    if "restaurante_backup_" in nombre_archivo:
                        nombre_sin_ext = nombre_archivo.replace(".db", "")
                        partes = nombre_sin_ext.split("restaurante_backup_")[-1].split("_")
                        if partes:
                            fecha_ref = partes[0]

                    conn = sqlite3.connect(ruta_db)
                    try:
                        filas = conn.execute(
                            """
                            SELECT e.codigo, e.nombre, e.apellidos, e.grado,
                                   CASE WHEN a.id IS NOT NULL THEN 'Presente' ELSE 'Ausente' END AS asistencia
                            FROM estudiantes e
                            LEFT JOIN asistencias a
                                ON e.tarjeta_identidad = a.tarjeta_estudiante
                               AND DATE(a.fecha_hora) = DATE(?)
                            ORDER BY e.apellidos, e.nombre
                            """,
                            (fecha_ref or datetime.now().strftime("%Y-%m-%d"),),
                        ).fetchall()
                        for fila in filas:
                            nombre_completo = f"{fila[1]} {fila[2]}".strip()
                            item_lista = {
                                "codigo": fila[0],
                                "nombre": nombre_completo,
                                "grado": fila[3],
                                "asistencia": fila[4],
                            }
                            if fila[4] == "Presente":
                                presentes.append(item_lista)
                            else:
                                ausentes.append(item_lista)
                    finally:
                        conn.close()
                except Exception:
                    presentes = []
                    ausentes = []
            return presentes, ausentes

        ruta_db = item.get("ruta")
        presentes, ausentes = cargar_asistencia_backup(ruta_db)

        lista_presentes = ft.ListView(expand=True, spacing=5, padding=5, auto_scroll=False)
        lista_ausentes = ft.ListView(expand=True, spacing=5, padding=5, auto_scroll=False)

        if presentes:
            for p in presentes:
                lista_presentes.controls.append(
                    ft.Text(f"✅ {p['codigo']} - {p['nombre']} - {p['grado']}", color="black")
                )
        else:
            lista_presentes.controls.append(ft.Text("No hay estudiantes presentes en este respaldo.", color="black"))

        if ausentes:
            for a in ausentes:
                lista_ausentes.controls.append(
                    ft.Text(f"❌ {a['codigo']} - {a['nombre']} - {a['grado']}", color="black")
                )
        else:
            lista_ausentes.controls.append(ft.Text("No hay estudiantes ausentes en este respaldo.", color="black"))

        lista_presentes.height = 180
        lista_ausentes.height = 180

        contenido_detalle = ft.Column(
            controls=[
                ft.Text(
                    f"Registro: {item['nombre']}",
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_VERDE_OSCURO,
                ),
                ft.Text(f"Fecha: {item.get('fecha', 'Sin fecha')}", color="black"),
                ft.TextField(
                    value=contenido,
                    multiline=True,
                    min_lines=8,
                    max_lines=12,
                    read_only=True,
                    expand=True,
                    text_size=12,
                    color="black",
                ),
                ft.Divider(color=COLOR_VERDE_LOGICO),
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text("Presentes", weight=ft.FontWeight.BOLD, color=COLOR_VERDE_OSCURO),
                                    lista_presentes,
                                ],
                                spacing=8,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            width=250,
                            height=220,
                            bgcolor="#F8F9FA",
                            border=ft.Border.all(1, "#D1D5DB"),
                            border_radius=8,
                            padding=10,
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text("Ausentes", weight=ft.FontWeight.BOLD, color="#E53935"),
                                    lista_ausentes,
                                ],
                                spacing=8,
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            width=250,
                            height=220,
                            bgcolor="#F8F9FA",
                            border=ft.Border.all(1, "#D1D5DB"),
                            border_radius=8,
                            padding=10,
                        ),
                    ],
                    spacing=20,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        )

        layout_registro = ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(130),
                    ft.Text(
                        "REGISTRO GUARDADO DEL DÍA",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    contenido_detalle,
                    ft.Button(
                        "🔙 Volver",
                        on_click=volver_al_historial,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=COLOR_BLANCO,
            width=700,
            padding=25,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000"),
        )

        mostrar_vista(
            ft.Container(
                content=layout_registro,
                alignment=ft.Alignment(0, 0),
                expand=True,
            )
        )

    def abrir_vista_historial(volver_callback, nombre_sesion):
        historial = db.listar_historial_reinicios()
        lista_historial = ft.ListView(expand=True, spacing=8, padding=10)

        def cargar_detalle(item):
            ruta_json = item.get("resumen")
            contenido = "No hay detalle disponible para este registro."
            if ruta_json and os.path.exists(ruta_json):
                try:
                    with open(ruta_json, "r", encoding="utf-8") as archivo:
                        contenido = archivo.read()
                except Exception:
                    contenido = "No se pudo leer el detalle del registro."

            detalle_registro.content = ft.Column(
                controls=[
                    ft.Text(
                        f"Registro del día: {item['nombre']}",
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    ft.TextField(
                        value=contenido,
                        multiline=True,
                        min_lines=12,
                        max_lines=18,
                        read_only=True,
                        expand=True,
                        text_size=12,
                        color="black",
                    ),
                ],
                spacing=10,
            )
            page.update()

        detalle_registro = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Registro del día guardado",
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    ft.Text(
                        "Seleccione un registro para ver su detalle.",
                        color="black",
                        size=12,
                    ),
                ],
                spacing=6,
            ),
            bgcolor="#F8F9FA",
            border=ft.Border.all(1, "#D1D5DB"),
            border_radius=8,
            padding=12,
        )

        def recargar_historial():
            abrir_vista_historial(volver_callback, nombre_sesion)

        if not historial:
            lista_historial.controls.append(
                ft.Text(
                    "Aún no hay reinicios guardados.",
                    color="#E53935",
                    weight=ft.FontWeight.BOLD,
                )
            )
        else:
            for item in historial:
                def eliminar_registro_historial_click(e, nombre=item["nombre"]):
                    exito, msg = db.eliminar_registro_historial(nombre)
                    page.snack_bar = ft.SnackBar(
                        ft.Text(msg),
                        bgcolor="#2A4B1A" if exito else "#D32F2F",
                    )
                    page.snack_bar.open = True
                    recargar_historial()

                lista_historial.controls.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    item["nombre"],
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_VERDE_OSCURO,
                                ),
                                ft.Text(
                                    f"Fecha: {item['fecha']} | Tamaño: {item['tamano_kb']} KB",
                                    color="black",
                                    size=12,
                                ),
                                ft.Row(
                                    controls=[
                                        ft.Button(
                                            "Ver Registro",
                                            on_click=lambda e, item=item: mostrar_registro_backup(
                                                item,
                                                volver_callback=lambda event: abrir_vista_historial(volver_callback, nombre_sesion),
                                                nombre_sesion=nombre_sesion,
                                            ),
                                            bgcolor=COLOR_VERDE_LOGICO,
                                            color="white",
                                        ),
                                        ft.Button(
                                            "Descargar CSV",
                                            on_click=lambda e, item=item: descargar_archivo(
                                                item["ruta"],
                                                item["nombre"],
                                                "csv",
                                            ),
                                            bgcolor=COLOR_AMARILLO_LOGO,
                                            color="white",
                                        ),
                                        ft.Button(
                                            "Eliminar Registro",
                                            on_click=eliminar_registro_historial_click,
                                            bgcolor="#D32F2F",
                                            color="white",
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
                                ),
                            ],
                            tight=True,
                        ),
                        bgcolor="#F8F9FA",
                        padding=10,
                        border_radius=8,
                        border=ft.Border.all(1, "#E5E7EB"),
                    )
                )

        layout_historial = ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(130),
                    ft.Text(
                        "HISTORIAL DE REINICIOS",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    ft.Text(
                        "Cada archivo representa un estado previo antes de reiniciar la plataforma.",
                        color="black",
                        size=12,
                    ),
                    ft.Container(
                        content=lista_historial,
                        height=260,
                        border=ft.Border.all(1, "#D1D5DB"),
                        border_radius=8,
                        padding=5,
                    ),
                    detalle_registro,
                    ft.Button(
                        "🔙 Volver",
                        on_click=volver_callback,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=COLOR_BLANCO,
            width=580,
            padding=25,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000"),
        )

        mostrar_vista(
            ft.Container(
                content=layout_historial,
                alignment=ft.Alignment(0, 0),
                expand=True,
            )
        )

    def construir_panel_admin(nombre_admin):
        txt_saludo = ft.Text(
            f"PANEL ADMINISTRADOR - {nombre_admin.upper()}",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=COLOR_VERDE_OSCURO,
        )
        txt_status_admin = ft.Text(
            value="Gestión de usuarios y sistema", color="black", size=13
        )
        horario_actual = db.obtener_horario()
        horarios_predefinidos = [
            ("11:00 - 11:30", "11:00", "11:30"),
            ("11:30 - 12:00", "11:30", "12:00"),
            ("12:00 - 12:30", "12:00", "12:30"),
            ("12:30 - 13:00", "12:30", "13:00"),
            ("Personalizado...", "custom", "custom"),
        ]
        horario_seleccionado = next(
            (
                f"{inicio}|{fin}"
                for _, inicio, fin in horarios_predefinidos
                if (inicio, fin)
                == (horario_actual["hora_inicio"], horario_actual["hora_fin"])
            ),
            "custom|custom",
        )
        es_horario_personalizado = horario_seleccionado == "custom|custom"
        horario_form = {
            "hora_inicio": horario_actual["hora_inicio"],
            "hora_fin": horario_actual["hora_fin"],
        }
        txt_horario_admin = ft.Text(
            value=f"Horario actual: {horario_actual['hora_inicio']} a {horario_actual['hora_fin']}",
            color="#2A4B1A",
            size=13,
            weight=ft.FontWeight.BOLD,
        )

        dd_horario_admin = ft.Dropdown(
            label="Seleccionar Horario",
            value=horario_seleccionado,
            options=[
                ft.dropdown.Option(text=texto, key=f"{inicio}|{fin}")
                for texto, inicio, fin in horarios_predefinidos
            ],
            color="black",
            height=50,
            width=300,
        )
        input_hora_inicio = ft.TextField(
            label="Apertura (HH:MM)",
            value=horario_actual["hora_inicio"],
            border_color="#D1D5DB",
            color="black",
            height=45,
            width=120,
            visible=es_horario_personalizado,
        )
        input_hora_fin = ft.TextField(
            label="Cierre (HH:MM)",
            value=horario_actual["hora_fin"],
            border_color="#D1D5DB",
            color="black",
            height=45,
            width=120,
            visible=es_horario_personalizado,
        )

        def actualizar_hora_inicio_admin(e):
            horario_form["hora_inicio"] = e.control.value

        def actualizar_hora_fin_admin(e):
            horario_form["hora_fin"] = e.control.value

        input_hora_inicio.on_change = actualizar_hora_inicio_admin
        input_hora_fin.on_change = actualizar_hora_fin_admin

        def cambiar_horario_admin(e):
            nonlocal es_horario_personalizado
            if not dd_horario_admin.value:
                return

            inicio, fin = dd_horario_admin.value.split("|", 1)
            es_horario_personalizado = inicio == "custom"
            input_hora_inicio.visible = es_horario_personalizado
            input_hora_fin.visible = es_horario_personalizado

            if not es_horario_personalizado:
                horario_form["hora_inicio"] = inicio
                horario_form["hora_fin"] = fin
                input_hora_inicio.value = inicio
                input_hora_fin.value = fin
                txt_status_admin.value = (
                    f"Horario seleccionado: {inicio} a {fin}. Presione Guardar Horario para aplicar."
                )
                txt_status_admin.color = COLOR_AMARILLO_LOGO
            else:
                txt_status_admin.value = (
                    "Ingrese las horas en formato HH:MM y presione Guardar Horario."
                )
                txt_status_admin.color = COLOR_AMARILLO_LOGO
            page.update()

        dd_horario_admin.on_select = cambiar_horario_admin

        input_nuevo_id = ft.TextField(
            label="Código ID Estudiante",
            border_color="#D1D5DB",
            color="black",
            height=45,
        )
        input_nuevo_nombre = ft.TextField(
            label="Nombre y Apellido Estudiante",
            border_color="#D1D5DB",
            color="black",
            height=45,
        )
        dd_nuevo_grado = ft.Dropdown(
            label="Grado",
            options=[ft.dropdown.Option(g) for g in db.grados_disponibles],
            value=db.grados_disponibles[0],
            color="black",
            height=45,
        )
        input_eliminar_id = ft.TextField(
            label="ID Estudiante a Eliminar",
            border_color="#D1D5DB",
            color="black",
            height=45,
            expand=True,
        )
        def agregar_estudiante(e):
            codigo = input_nuevo_id.value.strip() if input_nuevo_id.value else ""
            nombre = (
                input_nuevo_nombre.value.strip()
                if input_nuevo_nombre.value
                else ""
            )
            grado = dd_nuevo_grado.value

            if not (codigo and nombre and grado):
                txt_status_admin.value = "❌ Complete todos los campos."
                txt_status_admin.color = "#E53935"
            else:
                if not page._app_state.get("online", True):
                    guardar_cambio_pendiente(
                        "agregar_estudiante",
                        {"codigo": codigo, "nombre": nombre, "grado": grado, "tarjeta": codigo},
                    )
                    txt_status_admin.value = "Sin conexión: el estudiante se guardará localmente y se sincronizará al recuperar internet."
                    txt_status_admin.color = "#D32F2F"
                else:
                    exito, msg = db.agregar_estudiante_db(codigo, nombre, grado)
                    txt_status_admin.value = msg
                    txt_status_admin.color = (
                        COLOR_VERDE_LOGICO if exito else COLOR_AMARILLO_LOGO
                    )
                if page._app_state.get("online", True):
                    if txt_status_admin.value in ("", "Sin conexión: el estudiante se guardará localmente y se sincronizará al recuperar internet."):
                        pass
                    if not txt_status_admin.value.startswith("Sin conexión"):
                        if codigo and nombre and grado:
                            input_nuevo_id.value = ""
                            input_nuevo_nombre.value = ""
            page.update()

        def eliminar_estudiante(e):
            codigo = (
                input_eliminar_id.value.strip() if input_eliminar_id.value else ""
            )
            if not codigo:
                txt_status_admin.value = "⚠️ Ingrese un ID para eliminar."
                txt_status_admin.color = COLOR_AMARILLO_LOGO
            else:
                if not page._app_state.get("online", True):
                    guardar_cambio_pendiente("eliminar_estudiante", {"codigo": codigo})
                    txt_status_admin.value = "Sin conexión: la eliminación quedó pendiente y se aplicará al volver online."
                    txt_status_admin.color = "#D32F2F"
                else:
                    exito, msg = db.eliminar_estudiante_db(codigo)
                    txt_status_admin.value = msg
                    txt_status_admin.color = "#1E88E5" if exito else "#E53935"
                if page._app_state.get("online", True) and codigo:
                    input_eliminar_id.value = ""
            page.update()

        def guardar_horario_admin(e):
            nonlocal es_horario_personalizado
            if dd_horario_admin.value:
                inicio, fin = dd_horario_admin.value.split("|", 1)
                es_horario_personalizado = inicio == "custom"
                if es_horario_personalizado:
                    horario_form["hora_inicio"] = input_hora_inicio.value
                    horario_form["hora_fin"] = input_hora_fin.value
                else:
                    horario_form["hora_inicio"] = inicio
                    horario_form["hora_fin"] = fin

            if es_horario_personalizado and (
                not horario_form["hora_inicio"] or not horario_form["hora_fin"]
            ):
                txt_status_admin.value = "Ingrese la hora de apertura y de cierre."
                txt_status_admin.color = "#E53935"
                page.update()
                return

            if not page._app_state.get("online", True):
                guardar_cambio_pendiente(
                    "guardar_horario",
                    horario_form.copy(),
                )
                txt_status_admin.value = "Sin conexión: el horario quedó pendiente y se aplicará al recuperar internet."
                txt_status_admin.color = "#D32F2F"
                txt_horario_admin.value = (
                    f"Horario actual: {horario_form['hora_inicio']} a {horario_form['hora_fin']}"
                )
                page.update()
                return

            exito, msg = db.guardar_horario(
                horario_form["hora_inicio"],
                horario_form["hora_fin"],
            )
            horario_guardado = db.obtener_horario()
            txt_horario_admin.value = (
                f"Horario actual: {horario_guardado['hora_inicio']} a {horario_guardado['hora_fin']}"
            )
            txt_horario_admin.color = COLOR_VERDE_OSCURO if exito else "#E53935"
            txt_status_admin.value = msg
            txt_status_admin.color = COLOR_VERDE_LOGICO if exito else "#E53935"
            if exito:
                horario_form.update(horario_guardado)
                input_hora_inicio.value = horario_guardado["hora_inicio"]
                input_hora_fin.value = horario_guardado["hora_fin"]
                dd_horario_admin.value = next(
                    (
                        f"{inicio}|{fin}"
                        for _, inicio, fin in horarios_predefinidos
                        if (inicio, fin)
                        == (
                            horario_guardado["hora_inicio"],
                            horario_guardado["hora_fin"],
                        )
                    ),
                    "custom|custom",
                )
                es_horario_personalizado = (
                    dd_horario_admin.value == "custom|custom"
                )
                input_hora_inicio.visible = es_horario_personalizado
                input_hora_fin.visible = es_horario_personalizado
            page.update()

        def reiniciar_plataforma_admin(e):
            if not page._app_state.get("online", True):
                guardar_cambio_pendiente("reiniciar_plataforma", {})
                txt_status_admin.value = "Sin conexión: el reinicio quedó pendiente y se ejecutará al recuperar internet."
                txt_status_admin.color = "#D32F2F"
                page.update()
                return

            exito, msg = db.reiniciar_plataforma()
            txt_status_admin.value = msg
            txt_status_admin.color = COLOR_VERDE_LOGICO if exito else "#E53935"
            page.update()

        def ver_historial_admin(e):
            def volver_al_admin_desde_historial(e):
                    mostrar_vista(
                    ft.Container(
                        content=construir_panel_admin(nombre_admin),
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                    )
                )

            abrir_vista_historial(volver_al_admin_desde_historial, nombre_admin)

        def cerrar_sesion(e):
            limpiar_credenciales()
            mostrar_vista(layout_login)

        return ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(150),
                    txt_saludo,
                    ft.Divider(color=COLOR_VERDE_LOGICO),
                    txt_status_admin,
                    txt_horario_admin,
                    dd_horario_admin,
                    ft.Row(
                        controls=[
                            input_hora_inicio,
                            input_hora_fin,
                        ],
                        spacing=10,
                    ),
                    ft.Button(
                        "Guardar Horario",
                        on_click=guardar_horario_admin,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                    ft.Button(
                        "📊 Ver Base de Datos Completa",
                        on_click=lambda e: abrir_vista_base_datos(nombre_admin),
                        bgcolor=COLOR_VERDE_LOGICO,
                        color="white",
                        width=360,
                    ),
                    ft.Button(
                        "🔄 Reiniciar Plataforma",
                        on_click=reiniciar_plataforma_admin,
                        bgcolor="#D32F2F",
                        color="white",
                        width=360,
                    ),
                    ft.Button(
                        "🗂️ Historial de reinicios",
                        on_click=ver_historial_admin,
                        bgcolor="#5C6BC0",
                        color="white",
                        width=360,
                    ),
                    ft.Divider(),
                    ft.Text(
                        "Registrar Nuevo Estudiante:",
                        weight=ft.FontWeight.BOLD,
                        color="black",
                    ),
                    input_nuevo_id,
                    input_nuevo_nombre,
                    dd_nuevo_grado,
                    ft.Button(
                        "Agregar Estudiante",
                        on_click=agregar_estudiante,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                    ft.Divider(),
                    ft.Text(
                        "Eliminar Estudiante:",
                        weight=ft.FontWeight.BOLD,
                        color="black",
                    ),
                    ft.Row(
                        controls=[
                            input_eliminar_id,
                            ft.Button(
                                "Eliminar",
                                on_click=eliminar_estudiante,
                                bgcolor="#E53935",
                                color="white",
                            ),
                        ]
                    ),
                    ft.Divider(),
                    ft.TextButton(
                        "Cerrar Sesión",
                        on_click=cerrar_sesion,
                        style=ft.ButtonStyle(color="#E53935"),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=COLOR_BLANCO,
            width=480,
            padding=25,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000"),
        )

    # -------------------------------------------------------------------------
    # VISTA: ESCÁNER QR
    # -------------------------------------------------------------------------
    def abrir_pagina_escaner(nombre_docente):
        txt_estado_qr = ft.Text(
            "Apunte el código QR a la Cámara",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=COLOR_VERDE_OSCURO,
        )
        img_camara = ft.Image(
            src=bk.PIXEL_TRANSPARENTE, width=640, height=480, fit="contain"
        )

        dd_camara = ft.Dropdown(
            label="Cámara",
            value="0",
            options=[
                ft.dropdown.Option("0", "Cámara 0 (Integrada)"),
                ft.dropdown.Option("1", "Cámara 1 (Externa / USB)"),
                ft.dropdown.Option("2", "Cámara 2"),
            ],
            bgcolor="white",
            color="black",
            width=220,
            height=40,
        )

        dd_camara.on_change = lambda e: camara_mgr.iniciar_transmision(
            dd_camara.value, img_camara, txt_estado_qr, page
        )

        def volver_al_panel(e):
            camara_mgr.detener_camara()
            mostrar_vista(
                ft.Container(
                    content=construir_panel_docente(nombre_docente),
                    alignment=ft.Alignment(0, 0),
                    expand=True,
                )
            )

        layout_escaner = ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(150),
                    ft.Text(
                        "ESCÁNER DE CÓDIGO QR",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    txt_estado_qr,
                    ft.Row(
                        controls=[
                            dd_camara,
                            ft.Button(
                                "Reiniciar Cámara",
                                on_click=lambda e: camara_mgr.iniciar_transmision(
                                    dd_camara.value,
                                    img_camara,
                                    txt_estado_qr,
                                    page,
                                ),
                                bgcolor=COLOR_AMARILLO_LOGO,
                                color="white",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    ft.Container(
                        content=img_camara,
                        border=ft.Border.all(3, COLOR_VERDE_LOGICO),
                        border_radius=10,
                        bgcolor="black",
                    ),
                    ft.Button(
                        "Volver al Panel",
                        on_click=volver_al_panel,
                        bgcolor=COLOR_VERDE_LOGICO,
                        color="white",
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

        mostrar_vista(layout_escaner)
        camara_mgr.iniciar_transmision(
            dd_camara.value, img_camara, txt_estado_qr, page
        )

    # -------------------------------------------------------------------------
    # VISTA: PANEL DEL DOCENTE
    # -------------------------------------------------------------------------
    def construir_panel_docente(nombre_docente):
        txt_saludo = ft.Text(
            f"PANEL DOCENTE - {nombre_docente.upper()}",
            size=20,
            weight=ft.FontWeight.BOLD,
            color=COLOR_VERDE_OSCURO,
        )
        txt_logs = ft.Text(
            value="Bienvenido al sistema FoodPass.", color="black", size=14
        )
        horario_actual = db.obtener_horario()
        txt_horario_docente = ft.Text(
            value=f"📅 Horario de registro: {horario_actual['hora_inicio']} a {horario_actual['hora_fin']}",
            color="#2A4B1A",
            size=16,
            weight=ft.FontWeight.BOLD,
        )

        input_estudiante_id = ft.TextField(
            hint_text="ID Estudiante",
            border_color="#D1D5DB",
            color="black",
            height=50,
            text_size=16,
            expand=True,
            autofocus=True,
        )
        dd_filtro_grado = ft.Dropdown(
            label="Seleccionar Grado",
            options=[ft.dropdown.Option(g) for g in db.grados_disponibles],
            color="black",
            height=45,
            expand=True,
        )
        lista_resultados = ft.ListView(
            expand=True, spacing=5, padding=10, auto_scroll=True
        )

        def registrar_manual(e):
            id_ingresado = (
                input_estudiante_id.value.strip()
                if input_estudiante_id.value
                else ""
            )
            if not page._app_state.get("online", True):
                guardar_cambio_pendiente("marcar_asistencia", {"tarjeta_o_codigo": id_ingresado})
                txt_logs.value = "Sin conexión: la asistencia quedó guardada localmente y se sincronizará al recuperar internet."
                txt_logs.color = "#D32F2F"
                if id_ingresado:
                    db.registrar_asistencia(id_ingresado)
                    input_estudiante_id.value = ""
                page.update()
                return

            msg, color = bk.validar_y_registrar_manual(id_ingresado)
            txt_logs.value = msg
            txt_logs.color = color
            if color == "green":
                input_estudiante_id.value = ""
            page.update()

        input_estudiante_id.on_submit = registrar_manual

        def ir_a_vista_grados(e):
            if dd_filtro_grado.value:
                abrir_vista_grados(nombre_docente, dd_filtro_grado.value)
            else:
                txt_logs.value = "Debe seleccionar un grado primero."
                txt_logs.color = COLOR_AMARILLO_LOGO
                page.update()

        def ver_asistencias(e):
            lista_resultados.controls.clear()
            lista_resultados.controls.append(
                ft.Text(
                    "--- ASISTENTES DE HOY ---",
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_VERDE_OSCURO,
                )
            )
            datos, _ = bk.obtener_datos_base_datos()
            presentes = [u for u in datos if u["asistencia"] == "Presente"]

            for u in presentes:
                lista_resultados.controls.append(
                    ft.Text(
                        f"✅ [{u['codigo']}] {u['nombre']} - {u['grado']}",
                        color="black",
                    )
                )

            if not presentes:
                lista_resultados.controls.append(
                    ft.Text("No hay asistentes registrados hoy.", color="black")
                )
            page.update()

        def ver_ausentes(e):
            lista_resultados.controls.clear()
            lista_resultados.controls.append(
                ft.Text(
                    "--- AUSENTES DE HOY ---",
                    weight=ft.FontWeight.BOLD,
                    color="#E53935",
                )
            )
            datos, _ = bk.obtener_datos_base_datos()
            ausentes = [u for u in datos if u["asistencia"] == "Ausente"]

            for u in ausentes:
                lista_resultados.controls.append(
                    ft.Text(
                        f"❌ [{u['codigo']}] {u['nombre']} - {u['grado']}",
                        color="black",
                    )
                )

            if not ausentes:
                lista_resultados.controls.append(
                    ft.Text("No hay ausentes registrados hoy.", color="black")
                )
            page.update()

        def reiniciar_plataforma_docente(e):
            def confirmar_reinicio(e):
                dlg.open = False
                page.update()
                exito, msg = db.reiniciar_plataforma()
                txt_logs.value = msg
                txt_logs.color = COLOR_VERDE_LOGICO if exito else "#E53935"
                page.update()

            def cancelar_reinicio(e):
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("⚠️ Confirmar Reinicio"),
                content=ft.Text(
                    "¿Está seguro que desea reiniciar la plataforma?\n\n"
                    "Esta acción creará una copia de seguridad y borrará todas las asistencias del día.",
                    size=14
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=cancelar_reinicio),
                    ft.TextButton(
                        "Sí, Reiniciar",
                        on_click=confirmar_reinicio,
                        style=ft.ButtonStyle(color="#E53935")
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        def ver_historial_docente(e):
            def volver_al_docente_desde_historial(e):
                mostrar_vista(
                    ft.Container(
                        content=construir_panel_docente(nombre_docente),
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                    )
                )

            abrir_vista_historial(volver_al_docente_desde_historial, nombre_docente)

        def cerrar_sesion(e):
            limpiar_credenciales()
            mostrar_vista(layout_login)

        return ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(140),
                    txt_saludo,
                    ft.Divider(color=COLOR_VERDE_LOGICO, height=2),
                    txt_logs,
                    ft.Container(height=10),
                    # SECCIÓN: HORARIO DE REGISTRO
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "⏰ HORARIO DE REGISTRO",
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_VERDE_OSCURO,
                                ),
                                txt_horario_docente,
                                ft.Text(
                                    "Horario definido por el administrador",
                                    size=12,
                                    color="#616161",
                                ),
                            ],
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor="#F5F5F5",
                        padding=15,
                        border_radius=10,
                        border=ft.Border.all(2, COLOR_VERDE_OSCURO),
                    ),
                    ft.Container(height=5),
                    # SECCIÓN: REGISTRAR ASISTENCIA
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "📋 REGISTRAR ASISTENCIA",
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_VERDE_OSCURO,
                                ),
                                ft.Row(
                                    controls=[
                                        input_estudiante_id,
                                        ft.Container(
                                            content=ft.IconButton(
                                                icon=ft.Icons.CHECK_CIRCLE,
                                                icon_color="white",
                                                bgcolor=COLOR_VERDE_LOGICO,
                                                icon_size=35,
                                                on_click=registrar_manual,
                                                tooltip="Registrar Asistencia",
                                            ),
                                            bgcolor=COLOR_VERDE_OSCURO,
                                            border_radius=50,
                                            padding=3,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                ft.Button(
                                    "📷 Escáner QR",
                                    on_click=lambda e: abrir_pagina_escaner(nombre_docente),
                                    width=200,
                                    height=40,
                                    bgcolor=COLOR_AMARILLO_LOGO,
                                    color="white",
                                ),
                            ],
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        bgcolor="#E8F5E9",
                        padding=15,
                        border_radius=10,
                        border=ft.Border.all(2, COLOR_VERDE_LOGICO),
                    ),
                    ft.Container(height=5),
                    # SECCIÓN: CONSULTAR GRADO
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "🎓 CONSULTAR POR GRADO",
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_VERDE_OSCURO,
                                ),
                                ft.Row(
                                    controls=[
                                        dd_filtro_grado,
                                        ft.IconButton(
                                            icon=ft.Icons.SEARCH,
                                            icon_color="white",
                                            bgcolor=COLOR_AMARILLO_LOGO,
                                            icon_size=28,
                                            on_click=ir_a_vista_grados,
                                            tooltip="Consultar Grado",
                                        ),
                                    ],
                                    spacing=10,
                                ),
                            ],
                            spacing=10,
                        ),
                        bgcolor="#FFF9E6",
                        padding=15,
                        border_radius=10,
                        border=ft.Border.all(2, COLOR_AMARILLO_LOGO),
                    ),
                    ft.Container(height=5),
                    # SECCIÓN: VER ASISTENCIAS
                    ft.Text(
                        "📊 RESUMEN DEL DÍA",
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_VERDE_OSCURO,
                    ),
                    ft.Row(
                        controls=[
                            ft.Button(
                                "✅ Ver Presentes",
                                on_click=ver_asistencias,
                                bgcolor=COLOR_VERDE_LOGICO,
                                color="white",
                                expand=True,
                            ),
                            ft.Button(
                                "❌ Ver Ausentes",
                                on_click=ver_ausentes,
                                bgcolor="#E53935",
                                color="white",
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Container(
                        content=lista_resultados,
                        height=120,
                        border=ft.Border.all(1, "#D1D5DB"),
                        border_radius=8,
                        padding=5,
                    ),
                    ft.Divider(color="#CCCCCC"),
                    ft.Container(height=5),
                    ft.TextButton(
                        "🚪 Cerrar Sesión",
                        on_click=cerrar_sesion,
                        style=ft.ButtonStyle(color="#E53935"),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=COLOR_BLANCO,
            width=500,
            padding=25,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000"),
        )

    # -------------------------------------------------------------------------
    # VISTA: INICIO DE SESIÓN
    # -------------------------------------------------------------------------
    txt_cambiar_vista = ft.Text("Ir a Sesión Administrador", color="white")
    btn_cambiar_vista = ft.Button(
        content=txt_cambiar_vista,
        bgcolor=COLOR_AMARILLO_LOGO,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
    )
    lbl_titulo = ft.Text(
        "ACCESO DOCENTE",
        size=20,
        weight=ft.FontWeight.BOLD,
        color=COLOR_VERDE_OSCURO,
        text_align=ft.TextAlign.CENTER,
    )
    lbl_mensaje = ft.Text(
        value="", size=13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER
    )

    input_id = ft.TextField(
        hint_text="USUARIO",
        border_color="#D1D5DB",
        color="black",
        height=45,
        autofocus=True,
    )
    input_pass = ft.TextField(
        hint_text="CONTRASEÑA",
        password=True,
        can_reveal_password=True,
        border_color="#D1D5DB",
        color="black",
        height=45,
    )

    btn_iniciar = ft.Button(
        content=ft.Text("INICIAR SESIÓN", color="white"),
        bgcolor=COLOR_VERDE_LOGICO,
        height=45,
        width=360,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
    )

    contenido_formulario = ft.Column(
        controls=[input_id, input_pass, btn_iniciar],
        spacing=15,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    card_login = ft.Container(
        content=ft.Column(
            controls=[
                crear_logo(200),
                lbl_titulo,
                ft.Container(height=5),
                lbl_mensaje,
                ft.Container(height=10),
                contenido_formulario,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=COLOR_BLANCO,
        width=420,
        padding=30,
        border_radius=15,
        shadow=ft.BoxShadow(blur_radius=15, color="#1A000000"),
    )

    def validar_login(e):
        usuario = input_id.value.strip() if input_id.value else ""
        password = input_pass.value.strip() if input_pass.value else ""

        exito, nombre_usuario = bk.autenticar_usuario(
            usuario, password, es_admin
        )

        if exito:
            lbl_mensaje.value = ""
            panel = (
                construir_panel_admin(nombre_usuario)
                if es_admin
                else construir_panel_docente(nombre_usuario)
            )
            mostrar_vista(
                ft.Container(
                    content=panel, alignment=ft.Alignment(0, 0), expand=True
                )
            )
        else:
            lbl_mensaje.value = f"Credenciales incorrectas para {'Admin' if es_admin else 'Docente'}"
            lbl_mensaje.color = "#E53935"

        page.update()

    btn_iniciar.on_click = validar_login
    input_id.on_submit = validar_login
    input_pass.on_submit = validar_login

    def cambiar_modo(e):
        nonlocal es_admin
        es_admin = not es_admin

        input_id.value = ""
        input_pass.value = ""
        lbl_mensaje.value = ""

        if es_admin:
            page.title = "FoodPass - Ventana Administrador"
            txt_cambiar_vista.value = "Ir a Sesión Docente"
            lbl_titulo.value = "ACCESO ADMINISTRADOR"
        else:
            page.title = "FoodPass - Ventana Docente"
            txt_cambiar_vista.value = "Ir a Sesión Administrador"
            lbl_titulo.value = "ACCESO DOCENTE"

        page.update()

    btn_cambiar_vista.on_click = cambiar_modo

    # Crear fondo con imagen de restaurante
    contenido_login = ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=btn_cambiar_vista,
                    alignment=ft.Alignment(1, -1),
                    padding=10,
                ),
                ft.Container(
                    content=card_login,
                    alignment=ft.Alignment(0, 0) if hasattr(ft.alignment, 'center') else ft.Alignment(0, 0),
                    expand=True,
                ),
            ],
            expand=True,
        ),
        expand=True,
    )

    if IMAGEN_RESTAURANTE_BYTES:
        imagen_base64 = base64.b64encode(IMAGEN_RESTAURANTE_BYTES).decode("utf-8")
        layout_login = ft.Stack(
            controls=[
                ft.Container(
                    content=ft.Image(
                        src=f"data:image/png;base64,{imagen_base64}",
                        fit="cover",
                        opacity=0.25,
                    ),
                    expand=True,
                    width=9999,
                ),
                contenido_login,
            ],
            expand=True,
        )
    else:
        layout_login = contenido_login

    mostrar_vista(layout_login)


if __name__ == "__main__":
    ft.run(
        main=main,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8550")),
        view=ft.AppView.WEB_BROWSER,
    )