import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "restaurante.db"
conexion = sqlite3.connect(DB)
cursor = conexion.cursor()

cursor.execute("SELECT COUNT(*) FROM estudiantes")
total = cursor.fetchone()[0]

print(f"📊 Total de estudiantes en la base de datos: {total}")
conexion.close()