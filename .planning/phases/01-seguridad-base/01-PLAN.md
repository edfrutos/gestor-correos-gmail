# Phase 1 Plan: Seguridad y Base Operativa

## Objective

Endurecer la herramienta actual sin cambiar su propuesta de uso: seguir arrancando con `python3 server.py`, seguir sirviendo `index.html` y mantener búsqueda Gmail en modo readonly.

## Scope

- Eliminar dependencia de CORS abierto.
- Cambiar el frontend a endpoints relativos.
- Validar `sender` y `max` en `/api/search`.
- Separar estado pasivo de autenticación OAuth.
- Endurecer puntos de `innerHTML` con datos derivados del usuario o Gmail.
- Mantener compatibilidad con el README actual.

## Implementation Tasks

### Backend

- Sustituir `Access-Control-Allow-Origin: *` por una política cerrada o eliminar CORS si no hace falta.
- Añadir helper `parse_max(raw)` con rango permitido `1..100`.
- Añadir helper `validate_sender(raw)` para dominios y emails simples.
- Modificar `/api/status` para no llamar a `gmail()`.
- Devolver errores JSON consistentes con `status`, `error` y `detail`.
- Considerar `ThreadingHTTPServer` si se detecta bloqueo durante pruebas manuales.

### Frontend

- Cambiar `const API = 'http://localhost:8765'` por `const API = ''`.
- Escapar comillas en `esc()`.
- Revisar `lnk()` para crear enlaces seguros o validar URL antes de insertarla.
- Cambiar labels de fuentes y leyenda a `textContent` cuando sea viable.
- Mantener mensajes de UI en español.

### Documentation

- Actualizar `README.md` con instalación desde `requirements.txt`.
- Documentar que `credentials.json` y `token.json` no deben versionarse.
- Mantener `AGENTS.md` alineado si cambia el flujo de ejecución.

## Acceptance Criteria

- `python3 -m py_compile server.py` pasa.
- `python3 server.py` sirve la UI en `http://localhost:8765`.
- `/api/status` responde sin abrir OAuth.
- `/api/search?sender=plesk.com&max=30` funciona con sesión Gmail válida.
- `/api/search?sender=&max=abc` devuelve error controlado, no traceback.
- La UI puede buscar, filtrar, seleccionar, exportar y ocultar correos.
- Secretos y artefactos generados están cubiertos por `.gitignore`.

## Risks

- Cambiar CORS puede romper pruebas si la UI se abre como archivo local en vez de desde el servidor. La solución prevista es usar siempre `http://localhost:8765`.
- La sanitización de HTML debe hacerse sin degradar enlaces útiles en cuerpos de correo.
- Separar status de OAuth puede requerir ajustar mensajes de estado para no confundir "token ausente" con "error".

## Verification Commands

```bash
python3 -m py_compile server.py
python3 server.py
```

Manual:

- Abrir `http://localhost:8765`.
- Comprobar estado inicial.
- Buscar un dominio válido.
- Probar dominio inválido.
- Exportar un correo en TXT, Markdown y JSON.

## Out of Scope

- Persistencia local.
- Reglas editables.
- Reescritura del frontend.
- Acciones de escritura en Gmail.
