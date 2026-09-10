import csv
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB = str(BASE_DIR / "restaurante.db")
CSV_FILE = str(BASE_DIR / "DATABASE" / "estudiantes.csv")

def importar_estudiantes_csv(nombre_archivo):
    registrados = 0
    omitidos = 0
    errores = 0

    try:
        with open(nombre_archivo, mode='r', encoding='utf-8-sig') as archivo:
            muestra = archivo.read(2048)
            archivo.seek(0)
            delimitador = ';' if ';' in muestra else ','
            
            lector_csv = csv.DictReader(archivo, delimiter=delimitador)
            
            with sqlite3.connect(DB, timeout=10) as conexion:
                cursor = conexion.cursor()
                
                for fila in lector_csv:
                    # Limpiamos encabezados (quitar espacios, comillas y pasamos a mayúsculas para comparar fácil)
                    fila_limpia = {
                        str(k).replace('"', '').replace("'", "").strip().upper(): str(v).strip() 
                        for k, v in fila.items() if k
                    }
                    
                    # 1. Obtener CÓDIGO, TARJETA y GRADO
                    codigo = fila_limpia.get('CODIGO') or fila_limpia.get('CÓDIGO')
                    tarjeta = fila_limpia.get('TARJETA') or fila_limpia.get('TARJETA_IDENTIDAD') or fila_limpia.get('DOCUMENTO')
                    grado = fila_limpia.get('GRADO') or "S/D"

                    # 2. Unir NOMBRES (NOMBRE1 + NOMBRE2)
                    n1 = fila_limpia.get('NOMBRE1', '')
                    n2 = fila_limpia.get('NOMBRE2', '')
                    nombre = f"{n1} {n2}".strip() if (n1 or n2) else fila_limpia.get('NOMBRE', 'Sin Nombre')

                    # 3. Unir APELLIDOS (APELLIDO1 + APELLIDO2)
                    a1 = fila_limpia.get('APELLIDO1', '')
                    a2 = fila_limpia.get('APELLIDO2', '')
                    apellidos = f"{a1} {a2}".strip() if (a1 or a2) else fila_limpia.get('APELLIDOS', 'Sin Apellido')

                    # Si no hay código o tarjeta, saltamos la fila vacía
                    if not codigo or not tarjeta:
                        continue

                    try:
                        cursor.execute("""
                            INSERT INTO estudiantes (codigo, tarjeta_identidad, grado, nombre, apellidos)
                            VALUES (?, ?, ?, ?, ?)
                        """, (codigo, tarjeta, grado, nombre, apellidos))
                        registrados += 1
                    except sqlite3.IntegrityError as e:
                        if "UNIQUE" in str(e) or "PRIMARY KEY" in str(e):
                            omitidos += 1
                        else:
                            print(f"⚠️ Error en Código {codigo}: {e}")
                            errores += 1

        print(f"\n✅ Carga masiva finalizada con éxito:")
        print(f"   - 🟢 Registrados con éxito: {registrados}")
        print(f"   - 🟡 Omitidos (Ya existían en la BD): {omitidos}")
        if errores > 0:
            print(f"   - 🔴 Errores de formato: {errores}")

    except Exception as e:
        print(f"⚠️ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    from gestion_estudiantes import crear_tablas

    crear_tablas()
    importar_estudiantes_csv(CSV_FILE)