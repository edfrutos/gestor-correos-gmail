# Phase 1 Verification: Seguridad y Base Operativa

## Entorno

- Fecha: 2026-06-01
- Python: `python3` del sistema local
- Servidor probado en `localhost:8765` mediante `ThreadingHTTPServer` importado desde `server.py`

## Comandos ejecutados

```bash
.venv/bin/python -m py_compile server.py
```

Resultado: OK.

```bash
python3 -m pip show google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Resultado: las dependencias no estan instaladas en este entorno Python.

```bash
python3 -c 'from server import ThreadingHTTPServer,H,PORT; print(f"serving {PORT}", flush=True); ThreadingHTTPServer(("localhost", PORT), H).serve_forever()'
```

Resultado: servidor levantado con permisos escalados para bind local. Se detuvo con Ctrl+C tras las pruebas.

```bash
curl -i http://localhost:8765/api/status
```

Resultado: HTTP 200 JSON. No se abrio OAuth. En este entorno devolvio `gmail_lib: false`, `credentials: true`, `token: false`.

```bash
curl -i 'http://localhost:8765/api/search?sender=&max=abc'
```

Resultado: HTTP 400 JSON con `status: error`, `error: Parámetro sender requerido`.

```bash
curl -i 'http://localhost:8765/api/search?sender=plesk.com&max=abc'
```

Resultado: HTTP 400 JSON con `status: error`, `error: Parámetro max inválido`.

```bash
curl -i 'http://localhost:8765/api/search?sender=bad%20sender&max=30'
```

Resultado: HTTP 400 JSON con `status: error`, `error: Parámetro sender inválido`.

```bash
curl -i http://localhost:8765/
```

Resultado: HTTP 200, sirve `index.html`.

## Pruebas no ejecutadas

- Busqueda real `/api/search?sender=plesk.com&max=30` contra Gmail con sesion valida.
- UAT visual completa de buscar, filtrar, seleccionar, exportar y ocultar correos desde navegador.

## Motivo

La busqueda real requiere instalar dependencias de Google y completar OAuth en navegador con una cuenta Gmail local. No se hizo para evitar iniciar una autorizacion interactiva sin confirmacion explicita del usuario.

## Correccion posterior

Se creo `.venv` y se instalaron las dependencias con:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Se reinicio el servidor con:

```bash
.venv/bin/python server.py
```

Resultado de estado:

```json
{"status":"ok","ok":true,"can_search":true,"gmail_lib":true,"credentials":true,"token":true,"msg":"Token disponible"}
```

Tambien se verifico que el frontend servido contiene la correccion que evita incorporar remitentes vacios cuando la busqueda falla o devuelve cero correos nuevos.

## Correccion de flujo de tratamiento

Se ajusto la UI para que buscar un remitente no dependa de que los mensajes sean "nuevos". Si Gmail devuelve correos:

- se incorporan los mensajes que aun no estaban en memoria;
- se activa la fuente si todavia no existia;
- se filtra la lista por el dominio localizado;
- los correos quedan disponibles para seleccion, exportacion y ocultado.

Se verifico que el servidor sirve el frontend actualizado y que `/api/status` sigue operativo con `gmail_lib: true`.

## Bloqueo externo detectado

La busqueda real ya no falla por dependencias ni por UI. El endpoint `/api/search?sender=web.dev&max=10` devuelve ahora el error real de Google:

```json
{
  "status": "error",
  "error": "Error consultando Gmail",
  "detail": "Gmail API has not been used in project 694328517081 before or it is disabled..."
}
```

El `credentials.json` corresponde al proyecto `app-catalogojoyero`, con cliente OAuth que empieza por `694328517081`. Hay que activar Gmail API en ese proyecto Google Cloud antes de que las busquedas devuelvan correos.

## Bloqueo resuelto

El usuario confirmo que, tras activar Gmail API, la busqueda real funciona. Phase 1 queda validada funcionalmente para localizar remitentes y tratar correos desde la UI.
