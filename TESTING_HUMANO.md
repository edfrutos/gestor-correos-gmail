# Plan de Testeo Humano: Gestor de Inteligencia Gmail

Este documento guía al usuario a través de las pruebas manuales para verificar que todas las prestaciones de la aplicación funcionan según lo esperado.

> Suite automatizada: 195 tests, todas verdes (2026-10-18).
> Estado canónico: [`.planning/STATE.md`](.planning/STATE.md).

## 1. Configuración y Arranque
- [x] **Modo Estándar:** Ejecuta `.venv/bin/python server.py`. Verifica que se abre el navegador en `localhost:8765`.
- [x] **Modo Headless:** Ejecuta `HEADLESS=1 .venv/bin/python server.py`. Verifica que no abre navegador y muestra la URL en consola.
- [x] **Carga de .env:** Cambia el `PORT` en `.env` a `8888`, reinicia y verifica el cambio.

## 2. Búsqueda e Inteligencia
- [x] **Búsqueda por Remitente:** Busca `paypal.com`. Verifica que aparecen los correos y tienen categoría "💰 Monetario".
- [x] **Búsqueda por Fechas:** Limpia el remitente y busca un rango de 3 días. Verifica que aparecen correos de distintos remitentes.
- [x] **Búsqueda Literal:** Busca la palabra "factura" combinada con fechas. Verifica la precisión.

## 3. Gestión de Gmail (Acciones Reales)
- [x] **Archivado:** Selecciona un correo y pulsa "📦 Archivar".
    - [x] Verifica en la app que desaparece de la vista y va a "Ocultos".
    - [x] Verifica en Gmail Web que el correo ya no está en la bandeja de entrada (Recibidos).
- [x] **Etiquetado:** Selecciona un correo y pulsa "🏷 Etiquetar".
    - [x] Elige una etiqueta existente. Verifica en Gmail Web.
    - [x] Crea una etiqueta nueva (ej. `TEST_APP`) usando el buscador dinámico. Verifica en Gmail Web que se ha creado.

## 4. Automatización
- [x] **Regla Auto-Label:** Crea una regla para un remitente con "Aplicar etiqueta automáticamente". Busca ese remitente y verifica que los correos se etiquetan solos.
- [x] **Regla Auto-Archive:** Crea una regla con "Archivar automáticamente". Busca el remitente y verifica que los correos no llegan a aparecer en la bandeja de la app (van directos a ocultos).

## 5. Sugerencias IA (Opcional)
- [x] **Configuración IA desde la app (v1.2.6):** En el panel "🛠 Configuración" rellena URL base, modelo y clave y pulsa "Guardar configuración". Verifica que el estado pasa a "✓ Activa · <modelo>", que el campo de clave queda vacío con "•••• guardada" y que tras reiniciar la app sigue configurada.
- [x] **Modelo con razonamiento y modelo cloud (v1.2.7):** Con `qwen3:8b` (Ollama local), "Sugerir reglas ahora" propone reglas sin error de JSON. Con un modelo `…:cloud` el estado dice "remota (modelo cloud de Ollama…)" y sugerir reglas o el resumen IA piden confirmación antes de enviar.
- [x] **Activación:** Activa el toggle de IA en el panel de reglas.
- [x] **Aprendizaje:** Oculta 5 correos de un remitente nuevo.
- [x] **Sugerencia:** Pulsa "Sugerir reglas ahora". Verifica que la IA propone una regla coherente.
- [x] **Aplicación:** Pulsa "Aplicar" en la sugerencia y guarda la regla.

## 6. Exportación y Lector Integrado
- [x] **Exportación EML:** Selecciona un correo y pulsa "✉ Exportar EML".
    - [x] Verifica que aparece en el panel "📦 Exportaciones locales".
    - [x] Verifica que el archivo está físicamente en la carpeta `/exports` del proyecto.
- [x] **Visor Interno:** Haz clic en el correo exportado desde la lista.
    - [x] Verifica que se abre el visor interno (sin abrir Apple Mail).
    - [x] Comprueba que se ve el remitente, fecha, asunto y el cuerpo (HTML/Texto).
- [x] **Exportación ZIP:** Selecciona 3 correos y exporta. Verifica que el `.zip` se crea en `/exports`.
- [x] **Ruta real (v1.2.6):** En la app de escritorio, el texto bajo "📦 Exportaciones locales" muestra `~/Library/Application Support/GestorDeCorreos/exports` (desde fuente, la carpeta `exports` del proyecto).
- [x] **Carpeta de respaldo (v1.2.6):** En "🛠 Configuración" elige una carpeta con "📁 Elegir…" (o escribe la ruta) y guarda. Exporta un `.eml` y un `.zip`: ambos aparecen también en esa carpeta y el aviso dice "copiado a la carpeta de respaldo". Con una ruta que no existe, guardar da error claro.

## 7. Integración con el Sistema (Servicios)
- [x] **Abrir archivo externo:** Desde la terminal, ejecuta:
    `.venv/bin/python server.py --open "/ruta/a/cualquier/archivo.eml"`
    - [x] Verifica que la app se abre (o usa la instancia abierta) y muestra ese correo específico en el visor.
- [x] **Abrir `.eml` desde el Finder (app macOS):** con la `.app` **cerrada**, clic derecho en un `.eml` → "Abrir con → Gestor de Correos" → se abre la app y el visor muestra ese correo. Con la app **ya abierta**, repite con otro `.eml` → el visor lo muestra sin recargar la página (los resultados cargados siguen ahí).
    - La app es visor *alternativo* de `.eml`: el doble clic abre Apple Mail salvo que se elija "Obtener información → Abrir con → Cambiar todo…".
    - Para tener un `.eml`: "✉ Exportar EML" en la app (queda en `~/Library/Application Support/GestorDeCorreos/exports`) o "⋮ → Descargar mensaje" en Gmail web.

## 8. Seguridad y Mantenimiento
- [x] **Borrado Permanente:** Habilita `ENABLE_PERMANENT_DELETE=1`.
    - [x] Autoriza en la bandeja de ocultos.
    - [x] Borra un correo de prueba. Verifica que desaparece de Gmail (ni en papelera).
- [x] **Revocación:** Pulsa "Revocar autorización" y verifica que el acceso destructivo se cierra.

## 9. Auto-actualización (app macOS)
- [x] **Detección:** Con una `.app` instalada en una versión anterior a la publicada en GitHub Releases, pulsa **Buscar actualizaciones** (menú nativo o botón `#upd-check`). Verifica que informa de la versión nueva disponible.
- [x] **Descarga e instalación:** Acepta la actualización. Verifica que descarga el `.zip`, pide permiso, se reinstala y la app se relanza sola en la versión nueva (comprobar en "Acerca de" o en la pill de versión).
- [x] **Sin actualización:** Con la última versión ya instalada, pulsa **Buscar actualizaciones** de nuevo y verifica que informa de que ya tienes la versión más reciente.
- [x] **Sin Release publicado:** Si `latest.json` no existe todavía (HTTP 404), verifica el mensaje claro de "aún no hay ninguna versión publicada" en vez de un error genérico.
- [x] **Validación del zip (2026-10-18):** publica un Release nuevo construido con el `updater.py` que valida el zip antes de extraerlo, instálalo y desde esa versión repite **Detección** y **Descarga e instalación** contra el siguiente Release. Debe actualizar igual que antes (el zip legítimo pasa la validación).
- [x] **Manifiesto firmado:** con una versión que ya verifica la firma de `latest.json` instalada, repite **Detección** y **Descarga e instalación** contra el siguiente Release (con `latest.json.sig`). Debe actualizar igual. Opcional: con `GESTOR_UPDATE_MANIFEST_URL` apuntando a un `latest.json` sin `.sig` (o con la firma de otro), **Buscar actualizaciones** debe dar un error de firma, no "estás en la última versión".

- [x] **Puente a Sparkle (v1.3.0):** Desde la 1.2.7, **Buscar actualizaciones** instala la 1.3.0 con el updater de siempre. En la 1.3.0, `ls "/Applications/Gestor de Correos.app/Contents/Frameworks"` muestra `Sparkle.framework`.
- [x] **Sparkle (v1.3.0 → siguiente):** En la 1.3.0, **Buscar actualizaciones** (menú y botón ⟳) abre el diálogo de Sparkle: "estás al día" sin Release nuevo; con el siguiente Release, muestra la versión y las notas, descarga, instala y relanza la app en la versión nueva. _(2026-10-20: verificado 1.3.0 → 1.3.1: descarga, instala y relanza.)_
- [ ] **Delta de Sparkle (v1.3.1 → v1.4.0):** El build de la 1.4.0 muestra `OK, dist/GestorDeCorreos-1.4.0-from-1.3.1.delta` y el Release lleva ese `.delta` (la 1.3.2 no se publicó: sus cambios van en la 1.4.0). Desde la 1.3.1, **Buscar actualizaciones** instala la 1.4.0 y la app se relanza en la 1.4.0. En `log show --last 10m --predicate 'subsystem BEGINSWITH "org.sparkle-project"' --info` aparece la descarga del `.delta` (no la del `.zip`).


## 10. Mac App Store (Fase 35, v1.4.0)
Guía completa: `docs/MAC_APP_STORE.md`. Primero con la prueba local del sandbox (`MAS_LOCAL=1 … bash macos/build_mas.sh`, cerrando antes la app de Developer ID) y después con la build instalada desde TestFlight.
- [x] **Login en la app de Developer ID (v1.4.0):** Sin `token.json`, una búsqueda abre el login de Google en el navegador del sistema y, al aceptar, la app queda conectada.
- [x] **Arranque en sandbox:** La app abre y `codesign -d --entitlements - "dist-mas/Gestor de Correos.app"` muestra `com.apple.security.app-sandbox`. Los datos aparecen en `~/Library/Containers/com.edefrutos.gestorcorreos/Data/Library/Application Support/GestorDeCorreos/`. No hay menú «Actualizaciones» ni botón ⟳.
- [x] **Importar credentials.json:** En 🛠 Configuración → **📄 Importar credentials.json…**, elige tu `credentials.json`: aviso de éxito y el estado pasa a pedir autorización. Un JSON que no sea un cliente de escritorio da un error claro.
- [x] **OAuth en sandbox:** Una búsqueda abre el login de Google en el navegador. Al aceptar, la app queda conectada y la búsqueda devuelve resultados.
- [x] **Exportar y respaldo:** Con una carpeta elegida con **📁 Elegir…** (p. ej. en Documentos), exporta un `.eml`: aparece en `exports/` del contenedor y en la carpeta elegida. Sal de la app, vuelve a abrirla y exporta otro: la copia de respaldo sigue llegando (bookmark).
- [x] **Abrir .eml desde el Finder:** Doble clic (o «Abrir con») en un `.eml` lo muestra en el visor.
- [x] **IA local en sandbox:** Con Ollama en el Mac, «Sugerir reglas» o el resumen funcionan igual que en la app de Developer ID.
- [ ] **TestFlight:** La build subida con `build_mas.sh` se instala desde TestFlight y pasa las pruebas anteriores (con el cliente OAuth incluido si se usó `MAS_OAUTH_CLIENT`).

2026-10-20: §10 verificado en el Mac con la prueba local del sandbox
(`MAS_LOCAL=1`, v1.4.0): arranque aislado, importar `credentials.json`, login
OAuth en el navegador y búsqueda, exportar con respaldo recordado tras
reiniciar (bookmark), abrir `.eml` desde el Finder e IA local. La primera
build no arrancaba (`ModuleNotFoundError: _cffi_backend`, faltaba en el
bundle; arreglado en `macos/setup.py` + `macos/check_bundle.sh`). Pendiente
solo TestFlight (necesita certificados, perfil y ficha en App Store Connect).

2026-10-18: v1.2.4 (primer Release con `latest.json.sig`) instalado en el Mac
desde 1.2.3 por el auto-updater; esa actualización aún no verifica la firma
(la hace el updater de la 1.2.3). «Manifiesto firmado» queda para 1.2.4 → 1.2.5.

2026-10-19: parte opcional de «Manifiesto firmado» verificada en el Mac con
v1.2.4 y `GESTOR_UPDATE_MANIFEST_URL=file://…`: un `latest.json` con la versión
alterada (9.9.9) y la firma original da «La firma del manifiesto de
actualización no es válida»; sin `latest.json.sig` da «No se pudo consultar
actualizaciones…». En ningún caso ofrece la versión falsa.

2026-10-19: Release v1.2.5 (tag en `f39b5c7`) instalado en el Mac desde 1.2.4
por el auto-updater, primera actualización que verifica `latest.json.sig`;
«Acerca de» muestra 1.2.5. «Manifiesto firmado» completo.

Verificado en el Mac el 2026-10-18 con v1.2.2 → v1.2.3 (primera
actualización extraída por `_extract_zip`, con anti-downgrade en la versión
recibida). §2–§7 repasados tras Fase 32 Stage C y `odoc`: sin regresiones.

Verificado en el Mac el 2026-09-11 con Releases reales encadenados
(v1.1.0 → v1.2.0 → v1.2.1): detecta, descarga, verifica firma (`codesign`
+ `spctl` + `TeamIdentifier`) e instala. Nota: si la instancia de partida
tiene un updater anterior al fix de extracción de symlinks (`0a6afbb`), la primera
actualización automática no la repara — necesita una reinstalación manual
una vez (ver `macos/README.md`).
