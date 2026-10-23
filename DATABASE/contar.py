from pathlib import Path
import sys

DATABASE_DIR = Path(__file__).resolve().parent
if str(DATABASE_DIR) not in sys.path:
    sys.path.insert(0, str(DATABASE_DIR))

from gestion_estudiantes import get_connection

conexion = get_connection()
cursor = conexion.cursor()

cursor.execute("SELECT COUNT(*) FROM estudiantes")
total = cursor.fetchone()[0]

print(f"📊 Total de estudiantes en la base de datos: {total}")
conexion.close()