import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR / "DATABASE") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "DATABASE"))

from gestion_estudiantes import crear_tablas

if __name__ == "__main__":
    crear_tablas()