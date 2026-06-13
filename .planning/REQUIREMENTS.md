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

## Product Backlog

### Full Message Content Export

- [ ] **EXP-01**: El usuario puede exportar uno o varios correos seleccionados incluyendo el cuerpo íntegro de cada mensaje.
- [ ] **EXP-02**: La exportación completa incluye también las cabeceras y metadatos necesarios para identificar cada correo.
- [ ] **EXP-03**: La UI distingue claramente entre exportar un informe operativo y exportar el contenido completo de los correos seleccionados.
- [ ] **EXP-04**: La exportación completa obtiene el mensaje desde Gmail bajo demanda y no persiste cuerpos de correo en `app_state.json`.

### Private VPN Remote Deployment

- [ ] **NET-01**: La aplicación se ejecuta como servicio autónomo monousuario y puede accederse desde cualquier lugar mediante una VPN privada sobre Internet.
- [ ] **NET-02**: Sólo dispositivos autorizados en la VPN privada pueden alcanzar la aplicación; no existe acceso público directo.
- [ ] **NET-03**: El servidor restringe el puerto de la aplicación a la interfaz o red VPN y el firewall bloquea accesos desde Internet público.
- [ ] **NET-04**: Los tokens Gmail, credenciales OAuth y estado privado se almacenan fuera del repositorio con permisos y secretos adecuados para servidor.
- [ ] **NET-05**: El borrado permanente permanece desactivado por defecto y requiere controles reforzados en cualquier despliegue remoto.
- [ ] **NET-06**: El servidor deja de depender de `webbrowser.open`, permite configurar interfaz/puerto y valida la IP o nombre VPN autorizado.

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
| EXP-01 | Product backlog | Pending |
| EXP-02 | Product backlog | Pending |
| EXP-03 | Product backlog | Pending |
| EXP-04 | Product backlog | Pending |
| NET-01 | Product backlog | Pending |
| NET-02 | Product backlog | Pending |
| NET-03 | Product backlog | Pending |
| NET-04 | Product backlog | Pending |
| NET-05 | Product backlog | Pending |
| NET-06 | Product backlog | Pending |

**Coverage:**
- v1 requirements: 18 total
- v2 completed requirements: 6 total
- Completed requirements mapped to phases/hardening: 24
- v3 requirements: 13 total
- v3 mapped to phases: 13
- v4 requirements: 6 total
- v4 mapped to phases: 6
- v5 requirements: 7 total
- v5 mapped to phases: 3
- Post-v5 requirements: 2 total
- Post-v5 mapped to follow-up: 2
- Product backlog requirements: 10 total
- Unmapped active milestone: 0

---
*Requirements defined: 2026-05-31*
*Last updated: 2026-06-11 after completing phase 18 of v5.0*
