# 🎯 GUÍA RÁPIDA DE EJECUCIÓN - FOODPASS

## ✅ ESTADO DEL PROYECTO

**LIMPIEZA COMPLETADA:**
- ✅ Entornos virtuales duplicados eliminados (.venv, .venv-1, .venv-2, .venv-3)
- ✅ Carpetas __pycache__ eliminadas
- ✅ .gitignore actualizado
- ✅ Archivos de configuración para Railway creados
- ✅ Scripts de instalación y ejecución creados

---

## 🚀 PASOS PARA EJECUTAR LOCALMENTE

### Opción 1: Instalación Automática (Recomendada)

**Windows:**
```cmd
install.bat
run.bat
```

**Linux/macOS:**
```bash
chmod +x install.sh run.sh
./install.sh
./run.sh
```

### Opción 2: Instalación Manual

1. **Crear entorno virtual:**
   ```bash
   python -m venv .venv-foodpass
   ```

2. **Activar entorno virtual:**
   
   Windows (PowerShell):
   ```powershell
   .\.venv-foodpass\Scripts\Activate.ps1
   ```
   
   Linux/macOS:
   ```bash
   source .venv-foodpass/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Inicializar base de datos:**
   ```bash
   python DATABASE/crear_bd.py
   ```

5. **Ejecutar aplicación:**
   ```bash
   python FRONTEND/frontend.py
   ```

La aplicación se abrirá automáticamente en: **http://localhost:8550**

---

## 📦 PASOS PARA SUBIR A GITHUB

### 1. Inicializar Git (si no está inicializado)

```bash
git init
git add .
git commit -m "Initial commit: FoodPass application"
```

### 2. Crear repositorio en GitHub

1. Ve a https://github.com/new
2. Nombra tu repositorio: `foodpass` (o el nombre que prefieras)
3. NO inicialices con README (ya tenemos uno)
4. Crea el repositorio

### 3. Conectar y subir

```bash
git remote add origin https://github.com/TU_USUARIO/foodpass.git
git branch -M main
git push -u origin main
```

**Reemplaza `TU_USUARIO` con tu nombre de usuario de GitHub**

---

## 🚂 PASOS PARA DESPLEGAR EN RAILWAY

### 1. Crear cuenta en Railway

1. Ve a https://railway.app
2. Regístrate con GitHub (recomendado)

### 2. Crear nuevo proyecto

1. Haz clic en **"New Project"**
2. Selecciona **"Deploy from GitHub repo"**
3. Autoriza a Railway para acceder a tus repositorios
4. Selecciona el repositorio **foodpass**

### 3. Configuración automática

Railway detectará automáticamente:
- ✅ `runtime.txt` → Python 3.12
- ✅ `requirements.txt` → Dependencias
- ✅ `nixpacks.toml` → Build configuration
- ✅ `Procfile` → Comando de inicio

### 4. Deploy

1. Railway comenzará el despliegue automáticamente
2. Espera 3-5 minutos
3. Obtendrás una URL pública como:
   ```
   https://foodpass-production-xxxx.up.railway.app
   ```

### 5. Verificar el despliegue

1. Haz clic en **"Settings"** en el panel de Railway
2. En **"Networking"** verás tu **"Public URL"**
3. Abre la URL en tu navegador
4. Prueba con las credenciales:
   - Usuario: `admin`
   - Contraseña: `admin123`

---

## 🔍 ESTRUCTURA FINAL DEL PROYECTO

```
FOODPASS/
│
├── Backend/
│   └── backend.py                 # Lógica de negocio
│
├── DATABASE/
│   ├── crear_bd.py                # Inicialización de BD
│   ├── gestion_estudiantes.py     # CRUD estudiantes
│   ├── cargar_masivo.py           # Carga CSV
│   ├── contar.py                  # Utilidades
│   └── estudiantes.csv            # Datos iniciales
│
├── FRONTEND/
│   ├── frontend.py                # Interfaz principal
│   ├── logo.png                   # Logo
│   └── imagen_restaurante.png     # Imagen de fondo
│
├── .venv-foodpass/                # Entorno virtual (local)
├── historial_reinicios/           # Backups (ignorado en git)
│
├── .gitignore                     # Archivos ignorados
├── requirements.txt               # Dependencias Python
├── runtime.txt                    # Versión Python (Railway)
├── Procfile                       # Comando de inicio (Railway)
├── nixpacks.toml                  # Config build (Railway)
├── railway.json                   # Config Railway
│
├── install.bat                    # Instalador Windows
├── install.sh                     # Instalador Linux/Mac
├── run.bat                        # Ejecutar Windows
├── run.sh                         # Ejecutar Linux/Mac
│
├── README.md                      # Documentación principal
└── PASOS_EJECUCION.md            # Este archivo
```

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### Problema: PowerShell bloquea la ejecución de scripts

**Solución:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problema: La cámara no funciona

**Solución:**
- Verifica que opencv-python y pyzbar estén instalados
- Prueba con ingreso manual si no tienes cámara
- En Railway, la cámara no funcionará (usa ingreso manual)

### Problema: Railway no encuentra zbar

**Solución:**
El archivo `nixpacks.toml` ya incluye zbar en nixPkgs. Si hay error:
```toml
[phases.setup]
nixPkgs = ["python312", "zbar", "libGL"]
```

### Problema: El puerto no funciona en Railway

**Solución:**
Railway asigna el puerto automáticamente. Flet lo detecta. Si hay error, añade en Railway:
- Variable: `FLET_SERVER_PORT`
- Valor: `$PORT`

---

## 🎓 CREDENCIALES POR DEFECTO

### Modo Docente:
- **Usuario:** `docente`
- **Contraseña:** `docente123`

### Modo Administrador:
- **Usuario:** `admin`
- **Contraseña:** `admin123`

**⚠️ IMPORTANTE:** Cambia estas contraseñas después del primer uso.

---

## 📝 CHECKLIST FINAL

Antes de subir a GitHub y Railway:

- [x] Entornos virtuales duplicados eliminados
- [x] .gitignore configurado correctamente
- [x] requirements.txt actualizado
- [x] README.md completo
- [x] Scripts de instalación creados
- [x] Archivos de configuración Railway creados
- [x] Base de datos inicializada localmente
- [x] Aplicación probada localmente

---

## 📞 SOPORTE

Si tienes problemas:

1. Revisa los logs de Railway en la pestaña **"Deployments"**
2. Verifica que todos los archivos se hayan subido a GitHub
3. Asegúrate de que `runtime.txt` tenga `python-3.12.0`
4. Confirma que `requirements.txt` esté completo

---

**¡Listo para producción! 🚀**
