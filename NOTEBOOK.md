# Notebook

## Snapshot

**Fecha:** 2026-09-09
**Proyecto:** Gestor de Correos — Servidor Local
**Estado:** v1 → v9 completados (incl. app macOS firmada + notarizada);
v10 (auto-actualización) en curso. Suite: 156 tests, todas verdes.
Estado canónico: `.planning/STATE.md`.

El proyecto sirve una interfaz HTML desde `server.py`, autentica contra Gmail API en modo `gmail.readonly` y permite buscar, priorizar, agrupar, filtrar, exportar y tratar correos ocultos. El borrado permanente usa una autorización separada, revocable y desactivada por defecto.

## Hipótesis de Producto

La herramienta debe convertirse en un panel local de inteligencia operativa sobre correos técnicos: detectar avisos importantes, agrupar eventos, reducir ruido y acelerar decisiones sobre infraestructura.

El valor principal no es leer Gmail, sino transformar mensajes técnicos dispersos en una vista accionable.

## Observaciones Técnicas

- `server.py` concentra el servidor HTTP y las rutas; Gmail, validación, clasificación y persistencia viven en módulos separados.
- El frontend separa estructura (`index.html`), estilos (`static/app.css`), aplicación principal (`static/app.js`) y resúmenes/tendencias/AI (`static/summary.js`).
- Las fuentes fijas y personalizadas se consultan en Gmail al arrancar; el frontend ya no contiene correos incrustados.
- El ocultado local, reglas, fuentes añadidas, preferencias y auditoría mínima persisten en `app_state.json`.
- La API rechaza hosts/orígenes externos y limita los resultados reales de búsqueda.
- Reglas editables, resúmenes periódicos, tendencias, AI opcional, modularización frontend y ciclo de ocultos están completados.
- La bandeja de ocultos usa paginación de 20, selección por rangos y lotes destructivos de hasta 100 IDs.
- El token destructivo se reutiliza mientras sea válido o renovable y puede revocarse explícitamente.
- Los huérfanos se detectan y purgan de la referencia oculta y de la sesión cargada.
- La app ya dispone de logo y favicon locales.
- Las reglas base de clasificación y severidad viven **solo en el backend**
  (`classifier.py`) y el frontend las hidrata vía `/api/config` (Fase 22).
  `static/app.js:136` mantiene un fallback mínimo para modo sin conexión.
- Los huérfanos purgados no reaparecen tras recargar porque ya no existe el pool estático `BASE`.
- La vista de correo es un **modal** (Fase 30, v8); la hidratación de adjuntos
  ocurre al abrir el modal (`openEmailModal`), no al expandir la tarjeta.
- Archivado y etiquetado por lotes se trocean en tandas de 100 IDs
  (`BATCH_MODIFY_CHUNK`) y se rechazan lotes >1000 (Fase 33, ADR-010). El borrado
  permanente mantiene su tope de 100 y tandas de 20 (`DELETE_EXECUTION_CHUNK`).
- El front carga `shared.js → app.js → summary.js`. `static/shared.js` define
  `window.App`; la superficie compartida app.js→summary.js pasa por `App.*`
  (Fase 32, ADR-011). Hecho: `App.api`, `App.state.deleted`. Pendiente Stage C:
  `activeEmails`, `aiStatus`, `CATS` (se reasignan en `app.js`).
- App macOS (v9): `.app` pywebview firmada Developer ID + notarizada; el estado
  escribible se relocaliza a `~/Library/Application Support/GestorDeCorreos/`
  (`paths.py`), la app web/CLI no cambian. `VERSION` (raíz) = fuente única.
- Auto-actualización (v10, ADR-013): `updater.py` + `/api/update/{check,install}`
  + menú `pywebview`/botón `#upd-check`. Feed `latest.json` en GitHub Releases;
  antes de instalar verifica sha256 + `codesign`/`spctl` + `TeamIdentifier`.
  El servidor re-verifica el manifiesto; nunca instala una URL del cliente.

## Decisiones Iniciales

- Mantener la herramienta local-first: evita backend público y reduce superficie de exposición.
- Priorizar seguridad y fiabilidad antes de ampliar funciones.
- Mantener las operaciones normales en Gmail readonly y aislar el permiso destructivo completo en un token separado.
- Reutilizar el token destructivo entre sesiones, con revocación explícita disponible.
- Limitar el borrado permanente al contrato hidden-only, máximo 100 IDs y confirmación textual exacta.
- Evolucionar gradualmente: primero endurecer, después modularizar, después añadir inteligencia.

## Ideas de Alto Valor

- Bandeja de "atención requerida" con severidad y motivo.
- Agrupación por incidente: SSL, facturación, renovación, vulnerabilidad, backup, mantenimiento.
- Fuente de verdad Gmail para fuentes fijas y personalizadas, sin pool base incrustado.
- Reglas editables por usuario con alta, edición, borrado y operador de palabras clave `alguna`/`todas`.
- Resúmenes por periodo completados para 7/30 días; informes especializados por tipo de riesgo siguen siendo una posible ampliación.
- Exportación del contenido completo (`.eml`/`.zip` RFC822 desde Gmail `format=raw`)
  completada en la Fase 19 y persistida en `/exports`. La exportación *operativa*
  (Markdown/JSON) sigue siendo un artefacto distinto, de resumen.

## Próximas Preguntas

- Desplegar como servicio autónomo monousuario accesible desde cualquier lugar por Internet mediante VPN privada; no será una aplicación pública.
- ¿El objetivo principal es auditoría histórica, alerta diaria o reporting mensual?
- ¿Quieres que llegue a modificar Gmail, por ejemplo archivar o etiquetar, o debe seguir siendo solo lectura?
