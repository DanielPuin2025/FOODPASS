# FoodPass - Sistema de Control de Asistencia

FoodPass es una aplicación de gestión de asistencia para restaurantes escolares, desarrollada en Python con Flet. Utiliza SQLite como base de datos y soporta registro mediante código QR o ingreso manual.

## 🚀 Características

- **Autenticación de usuarios** (docentes y administradores)
- **Registro de asistencia** mediante QR o manual
- **Gestión de estudiantes** (alta, baja, consulta)
- **Control de horarios** configurables
- **Historial de asistencias** con estadísticas
- **Interfaz responsive** para web y escritorio

## 📋 Requisitos

- Python 3.12 o superior
- Cámara web (opcional, para escaneo QR)
- Sistema operativo: Windows, Linux o macOS

## 🔧 Instalación Local

### 1. Clonar el repositorio

```bash
git clone <tu-repositorio>
cd FOODPASS
```

### 2. Crear entorno virtual

**Windows (PowerShell):**
```powershell
python -m venv .venv-foodpass
.\.venv-foodpass\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv .venv-foodpass
source .venv-foodpass/bin/activate
```

### 3. Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Inicializar la base de datos

```bash
python DATABASE/crear_bd.py
```

### 5. Ejecutar la aplicación

```bash
python FRONTEND/frontend.py
```

La aplicación se abrirá automáticamente en tu navegador predeterminado en `http://localhost:8550`

## 🌐 Despliegue en Railway

### Paso 1: Preparar el repositorio

1. Inicializa Git (si no lo has hecho):
```bash
git init
git add .
git commit -m "Initial commit"
```

2. Sube tu código a GitHub:
```bash
git remote add origin <tu-repositorio-github>
git branch -M main
git push -u origin main
```

### Paso 2: Configurar Railway

1. Ve a [railway.app](https://railway.app) y crea una cuenta
2. Haz clic en "New Project" → "Deploy from GitHub repo"
3. Selecciona tu repositorio FOODPASS
4. Railway detectará automáticamente el proyecto Python

### Paso 3: Variables de entorno (opcional)

Si necesitas configuraciones específicas, añade variables en Railway:
- `PYTHON_VERSION`: 3.12.0 (ya está en runtime.txt)
- `PORT`: Railway lo asigna automáticamente

### Paso 4: Deploy

Railway desplegará automáticamente tu aplicación. Obtendrás una URL pública como:
```
https://foodpass-production.up.railway.app
```

## 🔑 Credenciales por Defecto

### Modo Docente
- **Usuario:** `docente`
- **Contraseña:** `docente123`

### Modo Administrador
- **Usuario:** `admin`
- **Contraseña:** `admin123`

**⚠️ Importante:** Cambia estas credenciales después del primer inicio de sesión.

## 📁 Estructura del Proyecto

```
FOODPASS/
├── Backend/
│   └── backend.py              # Lógica de negocio y cámara
├── DATABASE/
│   ├── crear_bd.py             # Inicialización de BD
│   ├── gestion_estudiantes.py  # CRUD de estudiantes
│   ├── cargar_masivo.py        # Carga desde CSV
│   └── estudiantes.csv         # Datos iniciales
├── FRONTEND/
│   ├── frontend.py             # Interfaz principal
│   ├── logo.png                # Logo de la app
│   └── imagen_restaurante.png  # Imagen de fondo
├── requirements.txt            # Dependencias Python
├── runtime.txt                 # Versión de Python
├── Procfile                    # Comando de inicio
├── nixpacks.toml              # Configuración Railway
├── railway.json               # Config Railway
└── README.md                  # Este archivo
```

## 🛠️ Uso de la Aplicación

### Registro de Asistencia

1. **Login:** Ingresa con tus credenciales
2. **Escaneo QR:** Coloca el código QR del estudiante frente a la cámara
3. **Ingreso Manual:** Escribe el ID del estudiante si no tienes cámara

### Gestión de Estudiantes (Admin)

1. **Agregar:** Completa el formulario con datos del estudiante
2. **Editar:** Busca al estudiante y modifica sus datos
3. **Eliminar:** Busca y elimina estudiantes del sistema
4. **Consultar:** Revisa el historial de asistencias

### Configuración de Horarios (Admin)

Define el rango horario en que se permite registrar asistencias.

## 📊 Base de Datos

El sistema utiliza SQLite con las siguientes tablas:

- **estudiantes:** Información de los estudiantes
- **asistencias:** Registro de asistencias con fecha/hora
- **usuarios:** Credenciales de docentes y administradores
- **configuracion:** Parámetros del sistema (horarios, etc.)

## 🐛 Solución de Problemas

### La cámara no funciona

Verifica que:
- Tienes `opencv-python` y `pyzbar` instalados
- La cámara está conectada y con permisos
- Otro programa no está usando la cámara

### Error al ejecutar en Railway

Railway requiere que:
- `nixpacks.toml` incluya `zbar` en nixPkgs (ya configurado)
- El puerto sea dinámico (Flet lo maneja automáticamente)
- La aplicación use Flet web mode (ya configurado)

### Base de datos vacía

Ejecuta:
```bash
python DATABASE/crear_bd.py
python DATABASE/cargar_masivo.py
```

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Añade nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 📧 Contacto

Para preguntas o soporte, abre un issue en el repositorio.

---

**Desarrollado con ❤️ para la gestión eficiente de comedores escolares**
