# Guía de Despliegue Remoto vía VPN

Esta guía explica cómo configurar el Gestor de Correos para funcionar en un servidor remoto (Mac Studio, Raspberry Pi, VPS, etc.) de forma segura a través de una VPN privada como Tailscale o WireGuard.

---

## 1. Requisitos

- VPN instalada en el servidor **y** en el cliente (ej. [Tailscale](https://tailscale.com), WireGuard).
- Python 3.10+ y entorno virtual configurado (`python3 -m venv .venv`).
- `credentials.json` de Google Cloud (tipo *Aplicación de escritorio*).
- `token.json` generado previamente con el flujo OAuth (ver nota al final).

---

## 2. Configuración (.env)

```bash
cp .env.example .env
```

Ejemplo para Tailscale con nombre de host:

```env
# Escuchar en todas las interfaces (incluida tailscale0)
HOST=0.0.0.0
PORT=8765

# No abrir navegador en el servidor
HEADLESS=1

# Orígenes permitidos — la barra final es opcional, ambos formatos funcionan
ALLOWED_ORIGINS=https://mi-servidor.tail1234.ts.net

# (Opcional) Borrado permanente
ENABLE_PERMANENT_DELETE=1

# (Opcional) IA — usar AI_BASE_URL, no AI_API_URL
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

> **Nota sobre `ALLOWED_ORIGINS`:** el servidor normaliza automáticamente la barra final, así que `https://host.ts.net/` y `https://host.ts.net` son equivalentes.

> **Nota sobre IA:** la variable correcta es **`AI_BASE_URL`** (URL base sin `/chat/completions`). El código construye el endpoint completo internamente.

---

## 3. Ejecución Persistente

### Opción A — Screen (macOS / Linux)
```bash
screen -S gestor-correos
cd /ruta/al/proyecto
.venv/bin/python server.py
# Ctrl+A, luego D para desconectar sin cerrar
```

Para reconectar:
```bash
screen -r gestor-correos
```

### Opción B — launchd (macOS, inicio automático)
Crea `~/Library/LaunchAgents/com.gestor-correos.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>         <string>com.gestor-correos</string>
  <key>WorkingDirectory</key> <string>/ruta/al/proyecto</string>
  <key>ProgramArguments</key>
  <array>
    <string>/ruta/al/proyecto/.venv/bin/python</string>
    <string>server.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOST</key>      <string>0.0.0.0</string>
    <key>PORT</key>      <string>8765</string>
    <key>HEADLESS</key>  <string>1</string>
  </dict>
  <key>RunAtLoad</key>    <true/>
  <key>KeepAlive</key>    <true/>
</dict>
</plist>
```
```bash
launchctl load ~/Library/LaunchAgents/com.gestor-correos.plist
```

### Opción C — Systemd (Linux)
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
```bash
sudo systemctl enable --now gestor-correos
```

---

## 4. Autorización OAuth en Modo Remoto (HEADLESS=1)

La forma **más sencilla** es generar el `token.json` localmente antes de mover el proyecto al servidor:

```bash
# En tu Mac local, con HEADLESS=0
.venv/bin/python server.py
# Realiza una búsqueda cualquiera → se abre el navegador → autoriza
# Ctrl+C para parar
# Copia token.json al servidor
scp token.json usuario@servidor:/ruta/al/proyecto/
```

Si necesitas autorizar directamente en el servidor:
1. Lanza el servidor con `HEADLESS=1`.
2. En la primera búsqueda, el servidor imprime la URL OAuth en la consola.
3. Copia esa URL y ábrela en el navegador de tu equipo local.
4. Completa el flujo de Google. El navegador intentará redirigir a `localhost`; ignora el error y copia la URL completa de la barra de direcciones.
5. En el servidor, pega esa URL directamente en el terminal donde corre el proceso (si el servidor tiene un listener en ese puerto).

---

## 5. Acceso desde el Navegador

Una vez arrancado, accede desde cualquier dispositivo en la misma VPN:

```
https://mi-servidor.tail1234.ts.net:8765
```

o, si usas la IP de Tailscale directamente:

```
http://100.x.y.z:8765
```

---

## 6. Seguridad

| Recomendación | Detalle |
|---------------|---------|
| **Firewall** | No expongas el puerto `8765` en la interfaz pública (`eth0`/`en0`). Solo debe ser accesible vía VPN. |
| **Secretos** | Nunca subas `.env`, `credentials.json`, `token.json`, `delete_token.json` ni `app_state.json` a repositorios. |
| **ALLOWED_ORIGINS** | Especifica exactamente los orígenes que necesitas; evita comodines. |
| **Borrado permanente** | Mantén `ENABLE_PERMANENT_DELETE=0` a menos que lo necesites activamente. |
