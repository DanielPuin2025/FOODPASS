import sys
import os

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "FRONTEND")
DATABASE_DIR = os.path.join(ROOT_DIR, "DATABASE")

for path in (ROOT_DIR, FRONTEND_DIR, DATABASE_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import flet as ft
import gestion_estudiantes as db
from frontend import main

if __name__ == "__main__":
    db.crear_tablas()
    ft.run(
        main=main,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8550")),
        view=ft.AppView.WEB_BROWSER,
    )
