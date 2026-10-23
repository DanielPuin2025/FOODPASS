# FoodPass

FoodPass es una aplicación web hecha en Python y Flet. Usa SQLite; no necesita
MySQL ni Apache para funcionar. En local guarda `restaurante.db` en la raíz.
En el contenedor, la base y los respaldos se guardan en el volumen configurado
en `FOODPASS_DATA_DIR`. Los horarios de asistencia y las fechas de registro
usan la hora de Colombia (UTC-5), incluso cuando el servidor está en otra zona.

## Instalación

Desde PowerShell, en la carpeta `C:\xampp\htdocs\FOODPASS`:

```powershell
py -m venv .venv-foodpass
.\.venv-foodpass\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación, ejecuta directamente:

```powershell
.\.venv-foodpass\Scripts\python.exe -m pip install -r requirements.txt
```

## Ejecución

```powershell
py DATABASE\crear_bd.py
py start_app.py
```

Se abrirá la aplicación en el navegador. También puedes usar el intérprete del
entorno virtual:

```powershell
.\.venv-foodpass\Scripts\python.exe start_app.py
```

## Demostración sin hosting

Puedes presentar el sistema desde un portátil conectado a la misma red Wi-Fi
que los equipos del jurado. La aplicación escucha en el puerto local `8550`.

En el portátil, consulta su dirección IP:

```powershell
ipconfig
```

Busca la `Dirección IPv4` de la conexión Wi-Fi, por ejemplo `192.168.1.25`.
Ejecuta la aplicación y comparte esta dirección con el jurado:

```text
http://192.168.1.25:8550
```

Todos los dispositivos deben estar conectados a la misma red y el portátil
debe permanecer encendido mientras dure la demostración. Si Windows Firewall
pregunta, permite Python en redes privadas. También puedes crear una regla
temporal como administrador:

```powershell
New-NetFirewallRule -DisplayName "FoodPass demo 8550" -Direction Inbound -Protocol TCP -LocalPort 8550 -Action Allow -Profile Private
```

Para una presentación sin Wi-Fi, conecta los dispositivos al punto de acceso
móvil del portátil o de un teléfono y repite `ipconfig` para obtener la IP.

## Credenciales iniciales

Estas credenciales solo se crean en modo de desarrollo local.

Modo docente:

- Usuario: `docente`
- Contraseña: `docente123`

Modo administrador:

- Usuario: `admin`
- Contraseña: `admin123`

También existen los usuarios `2001` / `docente123` y `3001` / `admin123`.

En producción no se crean estas cuentas de prueba. La primera inicialización
requiere configurar en el entorno del servicio las variables secretas
`FOODPASS_ADMIN_USER`, `FOODPASS_ADMIN_PASSWORD`, `FOODPASS_DOCENTE_USER` y
`FOODPASS_DOCENTE_PASSWORD`. Los usuarios deben ser distintos y cada contraseña
debe tener al menos 12 caracteres. Las contraseñas se almacenan con hash PBKDF2.

## Archivos de datos

- `restaurante.db`: base activa del sistema.
- `DATABASE\estudiantes.csv`: fuente de carga inicial, si la base no tiene estudiantes.
- `historial_reinicios\`: copias creadas al reiniciar la plataforma.
- `historial_reinicios\legacy\`: bases antiguas conservadas como referencia.

Si la base está vacía o necesitas agregar estudiantes, ingresa como administrador,
abre **Base de datos del sistema** y selecciona **Cargar estudiantes desde CSV**.
El archivo debe incluir las columnas `CODIGO` y `TARJETA_IDENTIDAD` (o
`DOCUMENTO`); se aceptan separadores coma o punto y coma. En Docker, el CSV
seleccionado se importa directamente a la base del volumen persistente y no es
necesario incluir datos de estudiantes en la imagen.

Las bases antiguas se conservan como referencia para no perder asistencias
históricas, pero la aplicación no las usa.

Desde el historial de reinicios, cada registro se puede descargar en formato
CSV. Al cerrar sesión como docente o administrador, se limpian los campos de
usuario y contraseña del formulario de acceso.

## Despliegue con Docker / Easypanel

El repositorio incluye un `Dockerfile`. Configura el servicio de Easypanel para
construir desde ese archivo y asigna el puerto interno `8550`. El puerto `3000`
corresponde al panel, no a la aplicación.

1. Crea un volumen persistente y móntalo en `/app/data`.
2. Configura las cuatro variables secretas de administrador/docente indicadas
   arriba antes del primer arranque. La aplicación se detendrá si faltan o si
   alguna contraseña tiene menos de 12 caracteres.
3. Si la base está vacía, inicia sesión como administrador, abre **Base de datos
   del sistema** y carga `estudiantes.csv` desde la opción **Cargar estudiantes
   desde CSV**. También puedes copiarlo al volumen como
   `/app/data/estudiantes.csv` antes del primer inicio. No subas ese archivo,
   las bases SQLite ni los respaldos a GitHub.
4. En Easypanel asigna el dominio `foodpass.programasena.online` al servicio y
   activa HTTPS. El DNS debe tener un registro A hacia la IP pública del
   servidor.
5. La app se sirve en la raíz del dominio. La ruta
   `/projects/sustentaciones2026` corresponde al panel de Easypanel, no a la
   dirección pública de FoodPass.

El lector QR actual abre una cámara conectada al proceso Python. En un
contenedor remoto no habrá cámara disponible por defecto; para escanear desde
el celular/navegador se necesita una integración de cámara del lado del cliente.