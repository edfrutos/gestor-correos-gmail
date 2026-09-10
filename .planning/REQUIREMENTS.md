# Requirements: Gestor de Correos — Servidor Local

**Defined:** 2026-05-31  
**Core Value:** Detectar y priorizar correos técnicos importantes sin exponer datos de Gmail fuera del equipo local.

## v1 Requirements

### Security

- [x] **SEC-01**: La API local rechaza orígenes externos no autorizados.
- [x] **SEC-02**: `credentials.json`, `token.json`, `.DS_Store` y artefactos generados están excluidos de Git.
- [x] **SEC-03**: `/api/status` no dispara autenticación OAuth ni abre navegador.
- [x] **SEC-04**: `/api/search` valida `sender` y limita el total real de mensajes mediante `max`.
- [x] **SEC-05**: La UI no inserta datos de Gmail o input de usuario sin escape seguro.

### Reliability

- [x] **REL-01**: El servidor gestiona errores de Gmail con respuestas JSON claras.
- [x] **REL-02**: Las búsquedas lentas no bloquean por completo otras peticiones locales.
- [x] **REL-03**: El proyecto incluye pruebas para fechas, remitentes, clasificación y endpoints.

### Product

- [x] **PROD-01**: El usuario ve una bandeja de acciones pendientes con severidad y motivo.
- [x] **PROD-02**: El usuario puede guardar fuentes añadidas y preferencias entre sesiones.
- [x] **PROD-03**: El usuario puede agrupar correos por proveedor con orden operativo determinista.
- [x] **PROD-04**: El usuario puede exportar informes limpios en Markdown y JSON.
- [x] **PROD-05**: El usuario ve en la cabecera de cada correo si hay adjuntos y puede abrirlos de forma accesible sin modificar Gmail.
- [x] **UI-01**: La interfaz usa una escala tipográfica mayor y proporcional según jerarquía y contexto, sin perder densidad operativa ni legibilidad responsive.

### Architecture

- [x] **ARCH-01**: La lógica Gmail se separa del servidor HTTP.
- [x] **ARCH-02**: La clasificación vive en un módulo testeable independiente.
- [x] **ARCH-03**: Existe almacenamiento local documentado para estado y preferencias.
- [x] **ARCH-04**: La documentación explica instalación, seguridad, ejecución y verificación.

## v2 Requirements

### Intelligence

- [x] **INT-01**: Resúmenes semanales o mensuales por proveedor y riesgo.
- [x] **INT-02**: Reglas editables desde la UI.
- [x] **INT-03**: Comparación de períodos, aumentos por proveedor/categoría y detección de asuntos recurrentes.
- [x] **INT-04**: Integración opcional con un modelo AI local/remoto para resumir informes operativos.

### Architecture and UI

- [x] **ARCH-05**: El frontend separa estructura, estilos, comportamiento principal y resúmenes sin introducir build tooling.
- [x] **UI-02**: Formularios, barras de acciones, avisos y modales evitan desbordes horizontales en escritorio y móvil.

### Gmail Write Actions

- **GML-01**: Etiquetar correos en Gmail desde la herramienta.
- **GML-02**: Archivar correos tratados.
- **GML-03**: Marcar como revisados o pendientes mediante labels.

## v3 Requirements

### Hidden Review

- [x] **HID-01**: El usuario puede abrir una bandeja dedicada que enumera todos los IDs ocultos y resuelve sus datos Gmail bajo demanda.
- [x] **HID-02**: El usuario puede seleccionar uno, varios o todos los correos ocultos disponibles.
- [x] **HID-03**: El usuario puede restaurar seleccionados como visibles o cerrar la revisión manteniéndolos ocultos.
- [x] **HID-04**: La bandeja distingue mensajes disponibles, no localizables y ya eliminados sin quedar bloqueada.

### Destructive Authorization

- [x] **AUTH-01**: Las operaciones normales conservan `gmail.readonly` y usan el token actual.
- [x] **AUTH-02**: El borrado permanente usa un token separado con el scope restringido `https://mail.google.com/`.
- [x] **AUTH-03**: La capacidad destructiva está desactivada por defecto y requiere habilitación local explícita.
- [x] **AUTH-04**: El estado de la API informa si el borrado permanente está deshabilitado, pendiente de autorización o autorizado.

### Permanent Deletion

- [x] **DEL-01**: El servidor sólo acepta borrar permanentemente IDs que figuran actualmente como ocultos locales.
- [x] **DEL-02**: El usuario debe confirmar el número exacto de mensajes mediante una frase escrita antes de ejecutar el borrado.
- [x] **DEL-03**: El contrato inicial de v3 limita cada solicitud a 20 mensajes y devuelve resultado individual por ID; DEL-06 amplía después el máximo actual a 100.
- [x] **DEL-04**: Tras un borrado confirmado, los IDs eliminados salen del estado oculto y se registra localmente una auditoría mínima sin contenido Gmail.
- [x] **DEL-05**: La UI comunica de forma inequívoca que el borrado es inmediato, permanente e irreversible.

## v4 Requirements

### Persistent Destructive Sessions

- [x] **AUTH-05**: El token destructivo válido se reutiliza automáticamente entre sesiones sin repetir OAuth mientras siga siendo válido.
- [x] **AUTH-06**: La API y la UI distinguen de forma explícita entre token ausente, válido, caducado y revocado antes de ejecutar acciones destructivas.

### Bulk Hidden Deletion

- [x] **HID-05**: El usuario puede construir una secuencia de ocultos a partir de páginas y rangos para preparar lotes grandes de borrado.
- [x] **DEL-06**: El usuario puede enviar hasta 100 IDs ocultos en una sola operación destructiva sin salir del contrato hidden-only.
- [x] **DEL-07**: El backend procesa lotes grandes en tandas acotadas, devuelve resultado individual por ID y mantiene una auditoría local mínima.
- [x] **DEL-08**: La UI muestra el tamaño total del lote y exige la confirmación exacta del total antes de habilitar el borrado.

## v5 Requirements

### Destructive Revocation

- [x] **AUTH-07**: El usuario puede revocar explícitamente `delete_token.json` desde la UI o la API sin afectar al resto del estado local.
- [x] **AUTH-08**: El estado de la API y la UI reflejan de forma inequívoca si el token destructivo se ha revocado, está ausente o sigue disponible para reutilización.

### Orphan Cleanup

- [x] **HID-06**: La limpieza local de huérfanos distingue claramente entre ocultos disponibles, no localizables y ya desconectados de Gmail.
- [x] **HID-07**: El usuario puede limpiar de forma controlada la información local de mensajes huérfanos sin tocar Gmail.
- [x] **HID-08**: El sistema evita que los huérfanos se confundan con mensajes operables en los flujos de revisión y mantenimiento.

### Operational Clarity

- [x] **UI-03**: La UI de mantenimiento hace más evidente qué acción afecta a Gmail y cuál sólo al estado local.
- [x] **UI-04**: El flujo de mantenimiento reduce fricción visual y mental al tratar token destructivo, ocultos huérfanos y acciones irreversibles.

### Post-v5 Reliability

- [x] **ARCH-06**: El frontend no incrusta contenido de correos y carga fuentes fijas y personalizadas desde Gmail.
- [x] **INT-05**: Las reglas personalizadas permiten exigir alguna o todas las palabras clave.

## v6 Requirements (completados)

### Full Message Content Export — Phase 19 (2026-06-12)

- [x] **EXP-01**: El usuario puede exportar uno o varios correos seleccionados incluyendo el cuerpo íntegro de cada mensaje.
- [x] **EXP-02**: La exportación completa incluye también las cabeceras y metadatos necesarios para identificar cada correo.
- [x] **EXP-03**: La UI distingue claramente entre exportar un informe operativo y exportar el contenido completo de los correos seleccionados.
- [x] **EXP-04**: La exportación completa obtiene el mensaje desde Gmail bajo demanda (`format=raw`) y no persiste cuerpos de correo en `app_state.json`.

### Private VPN Remote Deployment — Phase 20 (2026-06-12)

- [x] **NET-01**: La aplicación se ejecuta como servicio autónomo monousuario y puede accederse desde cualquier lugar mediante una VPN privada sobre Internet.
- [x] **NET-02**: Sólo dispositivos autorizados en la VPN privada pueden alcanzar la aplicación; no existe acceso público directo.
- [x] **NET-03**: El servidor restringe el puerto de la aplicación a la interfaz o red VPN y el firewall bloquea accesos desde Internet público (documentado en `docs/VPN_DEPLOYMENT.md`).
- [x] **NET-04**: Los tokens Gmail, credenciales OAuth y estado privado se almacenan fuera del repositorio con permisos y secretos adecuados para servidor.
- [x] **NET-05**: El borrado permanente permanece desactivado por defecto (`ENABLE_PERMANENT_DELETE=0`) y requiere controles reforzados en cualquier despliegue remoto.
- [x] **NET-06**: El servidor permite configurar interfaz/puerto (`HOST`/`PORT`) y modo headless (`HEADLESS=1`) en lugar de depender de `webbrowser.open`.

## v8 — Refinamiento UX y Mantenimiento (en curso)

- [x] **UX-01**: La vista de un correo se abre en un modal dedicado (subventana) con hidratación de adjuntos bajo demanda. — Phase 30
- [x] **UX-02**: Las categorías del panel lateral son reactivas y el estado de IA es reseteable. — Phase 30
- [x] **MNT-01**: La suite automatizada está 100 % verde (129/129; saneo de los 3 tests obsoletos). — Phase 31 (2026-09-08)
- [x] **MNT-02**: `static/*.js` reduce las dependencias cruzadas por variable global sin build tooling — espacio de nombres `App` (`static/shared.js`); `API` y `deleted` compartidos vía `App.*`; `summaryDays`/`summaryData` reubicados; sin `onclick` inline. — Phase 32 Stage A+B (2026-09-08). Seguimiento opcional: Stage C (`activeEmails`/`aiStatus`/`CATS`).
- [x] **MNT-03**: Archivado/etiquetado de lotes grandes troceado (`BATCH_MODIFY_CHUNK=100`) y acotado (`MAX_BATCH_MODIFY=1000`); aviso en UI >200. — Phase 33 (2026-09-08)

## v9 — App macOS nativa (rama `feat/macos-app`, en curso)

- [x] **MAC-01**: Existe una `.app` de macOS con ventana propia (WKWebView) que muestra la UI local y arranca/detiene `server.py`, sin romper la app web ni la CLI. — Phase 34 (2026-09-09; ventana verificada en el Mac)
- [x] **MAC-02**: Todo el estado escribible del `.app` vive en `~/Library/Application Support/GestorDeCorreos/`, nunca dentro del bundle; desde el código fuente sigue siendo la carpeta del proyecto. — Phase 34 (`paths.py` + rewiring, con tests)
- [x] **MAC-03**: El `.app` se firma con Developer ID Application, Hardened Runtime y entitlements mínimos, y se notariza y *staplea*. — Phase 34 (firma inside-out; `codesign -dv` → `flags=runtime`, Developer ID `V29BTBRY6G`, timestamp)
- [x] **MAC-04**: Build reproducible con `macos/build_app.sh` + variables de entorno documentadas; produce un DMG firmado y notarizado. — Phase 34 (`dist/GestorDeCorreos.dmg` notarizado + stapled, 2026-09-09)
- [x] **MAC-05**: `credentials.json` y el flujo OAuth de Gmail funcionan desde la app (usuario coloca `credentials.json` en Application Support). — Phase 34 (login Gmail verificado en el Mac)

## v10 — Auto-actualización (rama `feat/auto-update`, en curso)

- [x] **UPD-01**: La app ofrece "Buscar actualizaciones" en el menú nativo y en la UI web; muestra la versión en ejecución. — Phase 36
- [x] **UPD-02**: La comprobación consulta `latest.json` del último GitHub Release y compara con la versión del bundle. — Phase 36
- [x] **UPD-03**: Antes de instalar se verifica sha256 (manifiesto) + `codesign --verify --strict` + `spctl` (notarización) + `TeamIdentifier` esperado; cualquier fallo aborta. — Phase 36
- [x] **UPD-04**: La instalación requiere permiso explícito del usuario y luego sustituye la `.app` y relanza (helper *detached*; admin si hace falta). — Phase 36
- [x] **UPD-05**: `/api/update/install` re-verifica el manifiesto en el servidor y nunca instala una URL provista por el cliente; desde el código fuente la instalación automática está desactivada. — Phase 36
- [ ] **UPD-06**: Flujo real verificado en el Mac (Release de prueba → actualización desde versión anterior). — Phase 36 (pendiente)

## Out of Scope

| Feature | Reason |
|---------|--------|
| App pública multiusuario | Requiere autenticación, permisos y aislamiento de datos no previstos |
| Borrar mensajes que no estén ocultos localmente | Evita que la ruta destructiva se convierta en una API de borrado arbitrario |
| Etiquetar, archivar u otras modificaciones Gmail | Fuera del objetivo específico del milestone v3 |
| Base de datos remota | La propuesta actual debe ser local-first |
| Reescritura completa de UI | No aporta valor antes de corregir seguridad y arquitectura |
| Borrado arbitrario sin confirmación reforzada | El nuevo milestone amplía lotes, no la superficie destructiva |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | Phase 1 | Done |
| SEC-02 | Phase 1 | Done |
| SEC-03 | Phase 1 | Done |
| SEC-04 | Phase 1 | Done |
| SEC-05 | Phase 1 | Done |
| REL-01 | Phase 1 | Done |
| REL-02 | Phase 1 | Done |
| REL-03 | Phase 2 | Done |
| ARCH-01 | Phase 2 | Done |
| ARCH-02 | Phase 2 | Done |
| ARCH-03 | Phase 3 | Done |
| ARCH-04 | Phase 1 | Done |
| PROD-01 | Phase 4 | Done |
| PROD-02 | Phase 3 | Done |
| PROD-03 | Phase 4 | Done |
| PROD-04 | Phase 4 | Done |
| PROD-05 | Phase 3 follow-up | Done |
| UI-01 | Post-v1 hardening | Done |
| INT-02 | Phase 5 | Done |
| INT-01 | Phase 6 | Done |
| INT-03 | Phase 7 | Done |
| INT-04 | Phase 8 | Done |
| ARCH-05 | Phase 9 | Done |
| UI-02 | Post-v2 responsive hardening | Done |
| HID-01 | Phase 10 | Done |
| HID-02 | Phase 10 | Done |
| HID-03 | Phase 10 | Done |
| HID-04 | Phase 10 | Done |
| AUTH-01 | Phase 11 | Done |
| AUTH-02 | Phase 11 | Done |
| AUTH-03 | Phase 11 | Done |
| AUTH-04 | Phase 11 | Done |
| DEL-01 | Phase 12 | Done |
| DEL-02 | Phase 12 | Done |
| DEL-03 | Phase 12 | Done |
| DEL-04 | Phase 13 | Done |
| DEL-05 | Phase 13 | Done |
| AUTH-05 | Phase 14 | Done |
| AUTH-06 | Phase 14 | Done |
| HID-05 | Phase 15 | Done |
| DEL-06 | Phase 15 | Done |
| DEL-07 | Phase 15 | Done |
| DEL-08 | Phase 15 | Done |
| AUTH-07 | Phase 16 | Done |
| AUTH-08 | Phase 16 | Done |
| HID-06 | Phase 17 | Done |
| HID-07 | Phase 17 | Done |
| HID-08 | Phase 17 | Done |
| UI-03 | Phase 18 | Done |
| UI-04 | Phase 18 | Done |
| ARCH-06 | Post-v5 reliability | Done |
| INT-05 | Post-v5 reliability | Done |
| EXP-01 | Phase 19 | Done |
| EXP-02 | Phase 19 | Done |
| EXP-03 | Phase 19 | Done |
| EXP-04 | Phase 19 | Done |
| NET-01 | Phase 20 | Done |
| NET-02 | Phase 20 | Done |
| NET-03 | Phase 20 | Done |
| NET-04 | Phase 20 | Done |
| NET-05 | Phase 20 | Done |
| NET-06 | Phase 20 | Done |
| UX-01 | Phase 30 | Done |
| UX-02 | Phase 30 | Done |
| MNT-01 | Phase 31 | Done |
| MNT-02 | Phase 32 (Stage A+B) | Done · Stage C opcional |
| MNT-03 | Phase 33 | Done |
| MAC-01 | Phase 34 | Done |
| MAC-02 | Phase 34 | Done |
| MAC-03 | Phase 34 | Done |
| MAC-04 | Phase 34 | Done |
| MAC-05 | Phase 34 | Done |
| UPD-01 | Phase 36 | Done |
| UPD-02 | Phase 36 | Done |
| UPD-03 | Phase 36 | Done |
| UPD-04 | Phase 36 | Done |
| UPD-05 | Phase 36 | Done |
| UPD-06 | Phase 36 | Pending (verificación en Mac) |

**Coverage:**
- v1–v5 + post-v5: 57 requisitos, todos mapeados y Done.
- v6 (EXP-*, NET-*): 10 requisitos, Done (Fases 19–20).
- v8 (UX-*, MNT-*): 5 requisitos — 5 Done (Fases 30–33). MNT-02 con seguimiento
  opcional (Fase 32 Stage C).
- v9 (MAC-*): 5 requisitos — 5 Done (Fase 34; DMG firmado + notarizado verificado 2026-09-09).
- v10 (UPD-*): 6 requisitos — 5 Done (Fase 36, código + tests), 1 pendiente (verificación real en Mac).
- Unmapped: 0.

---
*Requirements defined: 2026-05-31*
*Last updated: 2026-09-09 — apertura de v10 (auto-actualización, rama `feat/auto-update`). Estado canónico: `.planning/STATE.md`.*
