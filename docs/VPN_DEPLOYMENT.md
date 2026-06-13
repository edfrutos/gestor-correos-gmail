# Guía de Despliegue Remoto vía VPN

Esta guía explica cómo configurar el Gestor de Correos para funcionar en un servidor remoto (ej. Mac Studio, Raspberry Pi, VPS) de forma segura a través de una VPN privada.

## 1. Requisitos
- Una VPN instalada en el servidor y en tu cliente (ej. [Tailscale](https://tailscale.com), WireGuard).
- Python 3.10+ y entorno virtual configurado.
- `credentials.json` configurado en la consola de Google (tipo Desktop).

## 2. Configuración (.env)
Copia el archivo de ejemplo y ajusta los valores:
```bash
cp .env.example .env
```

Edita `.env` con los datos de tu VPN:
```env
HOST=100.80.90.100  # Tu IP de Tailscale
PORT=8765
HEADLESS=1          # No abrir navegador en el servidor
ALLOWED_ORIGINS=100.80.90.100:8765
```

## 3. Ejecución Persistente
Para que el servidor siga funcionando tras cerrar la sesión SSH, usa `screen` o un servicio de sistema.

### Usando Screen:
```bash
screen -S gestor-correos
source .venv/bin/activate
export $(cat .env | xargs)
python server.py
# Presiona Ctrl+A y luego D para desconectar
```

### Usando Systemd (Linux):
Crea `/etc/systemd/system/gestor-correos.service`:
```ini
[Unit]
Description=Gestor de Correos Gmail
After=network.target

[Service]
User=tu_usuario
WorkingDirectory=/ruta/al/proyecto
EnvironmentFile=/ruta/al/proyecto/.env
ExecStart=/ruta/al/proyecto/.venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 4. Autorización OAuth Remota
Al usar `HEADLESS=1`, el servidor no podrá abrir el navegador para la autorización de Google.
1. Ejecuta el servidor.
2. Al realizar la primera búsqueda, verás un mensaje en la consola:
   `Please visit this URL to authorize this application: https://accounts.google.com/o/oauth2/auth...`
3. Copia esa URL y pégala en el navegador de tu **ordenador local**.
4. Sigue los pasos de Google. Al finalizar, el navegador local intentará conectar a `http://localhost:[PUERTO_ALEATORIO]`.
5. **Truco:** Como el servidor remoto está esperando en su propio puerto, el navegador local fallará. Copia la URL completa de la barra de direcciones (la que empieza por `http://localhost:[PUERTO]/?state=...&code=...`) y usa un túnel SSH temporal o simplemente asegúrate de que el flujo se complete si Google permite la redirección manual.

*Nota: La forma más fácil es realizar la primera autorización localmente, generar el `token.json` y luego mover la carpeta al servidor remoto.*

## 5. Seguridad
- **Firewall:** No abras el puerto `8765` en la interfaz pública (eth0). Solo debe ser accesible vía VPN (tailscale0).
- **Secretos:** Nunca subas `.env`, `credentials.json` o `*.json` a repositorios públicos.
