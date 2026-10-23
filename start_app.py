import sys
import os

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "FRONTEND")
DATABASE_DIR = os.path.join(ROOT_DIR, "DATABASE")

for path in (ROOT_DIR, FRONTEND_DIR, DATABASE_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import flet_web.fastapi as flet_fastapi
import uvicorn
import gestion_estudiantes as db
from frontend import main
from Backend.scanner_web import router as scanner_router


def crear_app():
    app = flet_fastapi.FastAPI()
    app.include_router(scanner_router)
    app.mount("/", flet_fastapi.app(main))
    return app


if __name__ == "__main__":
    db.crear_tablas()
    uvicorn.run(
        crear_app(),
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8550")),
        ws="websockets-sansio",
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
