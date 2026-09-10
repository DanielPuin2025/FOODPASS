import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "FRONTEND")
DATABASE_DIR = os.path.join(ROOT_DIR, "DATABASE")
BACKEND_DIR = os.path.join(ROOT_DIR, "Backend")
LOGO_PATH = os.path.abspath(os.path.join(FRONTEND_DIR, "logo.png"))
BACKGROUND_PATH = os.path.abspath(
    os.path.join(FRONTEND_DIR, "imagen_restaurante.png")
)
LOGO_BYTES = (
    open(LOGO_PATH, "rb").read() if os.path.exists(LOGO_PATH) else None
)
BACKGROUND_BYTES = (
    open(BACKGROUND_PATH, "rb").read()
    if os.path.exists(BACKGROUND_PATH)
    else None
)

for path in (ROOT_DIR, DATABASE_DIR, BACKEND_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import flet as ft
import gestion_estudiantes as db
import backend as bk


def main(page: ft.Page):
    # Inicializar las tablas SQLite en caso de que no existan
    db.crear_tablas()

    camara_mgr = bk.CamaraManager()

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

    def mostrar_vista(contenido):
        fondo = (
            ft.Image(
                src=BACKGROUND_BYTES,
                fit="fill",
                opacity=0.35,
                expand=True,
            )
            if BACKGROUND_BYTES is not None
            else ft.Container(bgcolor="#F2F4ED", expand=True)
        )
        page.clean()
        page.add(
            ft.Stack(
                controls=[fondo, contenido],
                fit=ft.StackFit.EXPAND,
                expand=True,
            )
        )
        page.update()

    # Componente reutilizable del Logo
    def crear_logo(width=180):
        src_logo = LOGO_BYTES if LOGO_BYTES is not None else "logo.png"
        return ft.Image(
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
                    ft.ElevatedButton(
                        "🔙 Volver al Panel Admin",
                        on_click=volver_al_admin,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
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
                    db.registrar_asistencia(tarjeta)
                    recargar_lista()

                acciones = [
                    ft.Text(
                        estado, color=color_estado, weight=ft.FontWeight.BOLD
                    )
                ]

                if not esta_presente:
                    btn_confirmar = ft.ElevatedButton(
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
                    ft.ElevatedButton(
                        "🔙 Volver al Panel Docente",
                        on_click=volver_al_panel,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
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
    def abrir_vista_historial(volver_callback, nombre_sesion):
        historial = db.listar_historial_reinicios()
        lista_historial = ft.ListView(expand=True, spacing=8, padding=10)

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
                        height=360,
                        border=ft.Border.all(1, "#D1D5DB"),
                        border_radius=8,
                        padding=5,
                    ),
                    ft.ElevatedButton(
                        "🔙 Volver",
                        on_click=volver_callback,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            bgcolor=COLOR_BLANCO,
            width=560,
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
        txt_horario_admin = ft.Text(
            value=f"Horario actual: {horario_actual['hora_inicio']} a {horario_actual['hora_fin']}",
            color="#2A4B1A",
            size=13,
            weight=ft.FontWeight.BOLD,
        )

        input_hora_inicio = ft.TextField(
            label="Hora de apertura",
            value=horario_actual["hora_inicio"],
            border_color="#D1D5DB",
            color="black",
            height=45,
        )
        input_hora_fin = ft.TextField(
            label="Hora de cierre",
            value=horario_actual["hora_fin"],
            border_color="#D1D5DB",
            color="black",
            height=45,
        )

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
                exito, msg = db.agregar_estudiante_db(codigo, nombre, grado)
                txt_status_admin.value = msg
                txt_status_admin.color = (
                    COLOR_VERDE_LOGICO if exito else COLOR_AMARILLO_LOGO
                )
                if exito:
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
                exito, msg = db.eliminar_estudiante_db(codigo)
                txt_status_admin.value = msg
                txt_status_admin.color = "#1E88E5" if exito else "#E53935"
                if exito:
                    input_eliminar_id.value = ""
            page.update()

        def guardar_horario_admin(e):
            exito, msg = db.guardar_horario(
                input_hora_inicio.value,
                input_hora_fin.value,
            )
            txt_horario_admin.value = (
                f"Horario actual: {db.obtener_horario()['hora_inicio']} a {db.obtener_horario()['hora_fin']}"
            )
            txt_horario_admin.color = COLOR_VERDE_OSCURO if exito else "#E53935"
            txt_status_admin.value = msg
            txt_status_admin.color = COLOR_VERDE_LOGICO if exito else "#E53935"
            page.update()

        def reiniciar_plataforma_admin(e):
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
            mostrar_vista(layout_login)

        return ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(150),
                    txt_saludo,
                    ft.Divider(color=COLOR_VERDE_LOGICO),
                    txt_status_admin,
                    txt_horario_admin,
                    ft.Row(
                        controls=[
                            input_hora_inicio,
                            input_hora_fin,
                        ],
                        spacing=10,
                    ),
                    ft.ElevatedButton(
                        "Guardar Horario",
                        on_click=guardar_horario_admin,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                    ft.ElevatedButton(
                        "📊 Ver Base de Datos Completa",
                        on_click=lambda e: abrir_vista_base_datos(nombre_admin),
                        bgcolor=COLOR_VERDE_LOGICO,
                        color="white",
                        width=360,
                    ),
                    ft.ElevatedButton(
                        "🔄 Reiniciar Plataforma",
                        on_click=reiniciar_plataforma_admin,
                        bgcolor="#D32F2F",
                        color="white",
                        width=360,
                    ),
                    ft.ElevatedButton(
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
                    ft.ElevatedButton(
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
                            ft.ElevatedButton(
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
                            ft.ElevatedButton(
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
                    ft.ElevatedButton(
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
            size=18,
            weight=ft.FontWeight.BOLD,
            color=COLOR_VERDE_OSCURO,
        )
        txt_logs = ft.Text(
            value="Bienvenido al sistema FoodPass.", color="black", size=13
        )
        horario_actual = db.obtener_horario()
        txt_horario_docente = ft.Text(
            value=f"Horario de registro: {horario_actual['hora_inicio']} a {horario_actual['hora_fin']}",
            color="#2A4B1A",
            size=13,
            weight=ft.FontWeight.BOLD,
        )
        input_hora_inicio = ft.TextField(
            label="Apertura",
            value=horario_actual["hora_inicio"],
            border_color="#D1D5DB",
            color="black",
            height=45,
            expand=True,
        )
        input_hora_fin = ft.TextField(
            label="Cierre",
            value=horario_actual["hora_fin"],
            border_color="#D1D5DB",
            color="black",
            height=45,
            expand=True,
        )
        input_estudiante_id = ft.TextField(
            hint_text="ID Estudiante",
            border_color="#D1D5DB",
            color="black",
            height=45,
            expand=True,
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
            msg, color = bk.validar_y_registrar_manual(id_ingresado)
            txt_logs.value = msg
            txt_logs.color = color
            if color == "green":
                input_estudiante_id.value = ""
            page.update()

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

        def guardar_horario_docente(e):
            exito, msg = db.guardar_horario(
                input_hora_inicio.value,
                input_hora_fin.value,
            )
            txt_horario_docente.value = (
                f"Horario de registro: {db.obtener_horario()['hora_inicio']} a {db.obtener_horario()['hora_fin']}"
            )
            txt_horario_docente.color = COLOR_VERDE_OSCURO if exito else "#E53935"
            txt_logs.value = msg
            txt_logs.color = COLOR_VERDE_LOGICO if exito else "#E53935"
            page.update()

        def reiniciar_plataforma_docente(e):
            exito, msg = db.reiniciar_plataforma()
            txt_logs.value = msg
            txt_logs.color = COLOR_VERDE_LOGICO if exito else "#E53935"
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
            mostrar_vista(layout_login)

        return ft.Container(
            content=ft.Column(
                controls=[
                    crear_logo(160),
                    txt_saludo,
                    ft.Divider(color=COLOR_VERDE_LOGICO),
                    txt_logs,
                    txt_horario_docente,
                    ft.Row(
                        controls=[
                            input_hora_inicio,
                            input_hora_fin,
                        ],
                        spacing=10,
                    ),
                    ft.ElevatedButton(
                        "Guardar Horario",
                        on_click=guardar_horario_docente,
                        bgcolor=COLOR_AMARILLO_LOGO,
                        color="white",
                        width=360,
                    ),
                    ft.Row(
                        controls=[
                            input_estudiante_id,
                            ft.ElevatedButton(
                                "Registrar ID",
                                on_click=registrar_manual,
                                bgcolor=COLOR_AMARILLO_LOGO,
                                color="white",
                            ),
                        ]
                    ),
                    ft.ElevatedButton(
                        "📷 Abrir Página de Escáner QR",
                        on_click=lambda e: abrir_pagina_escaner(nombre_docente),
                        width=360,
                        bgcolor=COLOR_VERDE_LOGICO,
                        color="white",
                    ),
                    ft.ElevatedButton(
                        "🔄 Reiniciar Plataforma",
                        on_click=reiniciar_plataforma_docente,
                        width=360,
                        bgcolor="#D32F2F",
                        color="white",
                    ),
                    ft.ElevatedButton(
                        "🗂️ Historial de reinicios",
                        on_click=ver_historial_docente,
                        width=360,
                        bgcolor="#5C6BC0",
                        color="white",
                    ),
                    ft.Divider(),
                    ft.Row(
                        controls=[
                            dd_filtro_grado,
                            ft.ElevatedButton(
                                "Consultar Grado",
                                on_click=ir_a_vista_grados,
                                bgcolor=COLOR_AMARILLO_LOGO,
                                color="white",
                            ),
                        ]
                    ),
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(
                                "Asistentes", on_click=ver_asistencias
                            ),
                            ft.OutlinedButton(
                                "Ausentes", on_click=ver_ausentes
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Container(
                        content=lista_resultados,
                        height=120,
                        border=ft.Border.all(1, "#D1D5DB"),
                        border_radius=8,
                        padding=5,
                    ),
                    ft.TextButton(
                        "Cerrar Sesión",
                        on_click=cerrar_sesion,
                        style=ft.ButtonStyle(color="#E53935"),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10,
            ),
            bgcolor=COLOR_BLANCO,
            width=480,
            padding=25,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=15, color="#1A000000"),
        )

    # -------------------------------------------------------------------------
    # VISTA: INICIO DE SESIÓN
    # -------------------------------------------------------------------------
    txt_cambiar_vista = ft.Text("Ir a Sesión Administrador", color="white")
    btn_cambiar_vista = ft.ElevatedButton(
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
    )
    input_pass = ft.TextField(
        hint_text="CONTRASEÑA",
        password=True,
        can_reveal_password=True,
        border_color="#D1D5DB",
        color="black",
        height=45,
    )

    btn_iniciar = ft.ElevatedButton(
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

    layout_login = ft.Column(
        controls=[
            ft.Row(
                controls=[btn_cambiar_vista],
                alignment=ft.MainAxisAlignment.END,
            ),
            ft.Container(
                content=card_login, alignment=ft.Alignment(0, 0), expand=True
            ),
        ],
        expand=True,
    )

    mostrar_vista(layout_login)


if __name__ == "__main__":
    ft.run(
        main=main,
        host="0.0.0.0",
        port=8550,
        view=ft.AppView.WEB_BROWSER,
    )

