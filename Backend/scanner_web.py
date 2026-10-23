"""Escáner QR en el navegador: página estática + endpoint /api/scan con token firmado."""
import base64
import hashlib
import hmac
import os
import secrets
import time

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import gestion_estudiantes as db

ESCANER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "FRONTEND", "escaner")
)
TOKEN_TTL = 8 * 3600
_SECRET = (os.environ.get("FOODPASS_SCAN_SECRET") or secrets.token_hex(32)).encode()


def _firma(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def crear_token(usuario: str) -> str:
    exp = int(time.time()) + TOKEN_TTL
    payload = base64.urlsafe_b64encode(f"{usuario}|{exp}".encode()).decode()
    return f"{payload}.{_firma(payload)}"


def token_valido(token: str) -> bool:
    try:
        payload, firma = token.split(".", 1)
        if not hmac.compare_digest(firma, _firma(payload)):
            return False
        _, exp = base64.urlsafe_b64decode(payload.encode()).decode().rsplit("|", 1)
        return int(exp) > time.time()
    except Exception:
        return False


class ScanIn(BaseModel):
    token: str
    codigo: str


router = APIRouter()


@router.get("/escaner")
def pagina_escaner():
    return FileResponse(
        os.path.join(ESCANER_DIR, "index.html"),
        headers={"Cache-Control": "no-store", "Permissions-Policy": "camera=(self)"},
    )


@router.get("/escaner/jsQR.js")
def lib_jsqr():
    return FileResponse(
        os.path.join(ESCANER_DIR, "jsQR.js"), media_type="application/javascript"
    )


@router.post("/api/scan")
def escanear(datos: ScanIn):
    if not token_valido(datos.token):
        return JSONResponse(
            {"ok": False, "mensaje": "Sesión del escáner vencida. Vuelva a abrirlo desde el panel."},
            status_code=401,
        )
    codigo = datos.codigo.strip()[:100]
    if not codigo:
        return {"ok": False, "mensaje": "Código vacío."}
    ok, mensaje = db.registrar_asistencia(codigo)
    return {"ok": ok, "mensaje": mensaje}
