# Feedback Técnico y de Producto

> Revisión viva sincronizada el 2026-09-08. Milestones v1 → v7.5 completados;
> v8 (refinamiento UX) en curso. Suite: **136 pruebas, todas verdes** (Fases 31–33).
> Estado canónico: [`.planning/STATE.md`](.planning/STATE.md).

## Sinopsis
La herramienta ha evolucionado de un panel de lectura local a un gestor de inteligencia operativa bidireccional. Ahora permite organizar la bandeja de entrada real de Gmail mediante archivado, etiquetado y automatización inteligente, manteniendo una seguridad estricta y permitiendo el despliegue remoto seguro vía VPN.

## Problemas Resueltos (v1 - v7)

### 1. Gestión Integral de Gmail
- **Resuelto**: La app puede archivar (retirar INBOX) y gestionar etiquetas (listar, aplicar y crear dinámicamente) sin salir de la interfaz.

### 2. Exportación de Contenido Íntegro
- **Resuelto**: El usuario puede descargar archivos `.eml` (RFC822 crudo) o lotes en `.zip` con el contenido completo, incluyendo adjuntos originales.

### 3. Deuda de Duplicidad (Reglas)
- **Resuelto**: Se han unificado las categorías, colores y palabras clave en el backend (`classifier.py`), hidratando el frontend vía `/api/config`.

### 4. Despliegue Remoto y VPN
- **Resuelto**: Configuración completa por variables de entorno, modo headless para servidores SSH y carga automática de `.env`.

### 5. Búsqueda Avanzada
- **Resuelto**: Integración de filtros por fechas (`after`/`before`) y texto literal nativo de Gmail, permitiendo búsquedas de contexto general.

## Próximas Mejoras Recomendadas

- **Soporte Multi-cuenta**: Gestionar múltiples perfiles de Gmail desde la misma instancia del servidor.
- **Sincronización AI Automática**: Permitir que las sugerencias de la IA se apliquen como "reglas temporales" para limpiezas masivas puntuales.
- **Análisis de Adjuntos**: Filtrado avanzado por tipo de archivo, extensión y tamaño real detectado en Gmail.
- **Histórico de Acciones**: Panel de auditoría detallado para revisar qué reglas automáticas han archivado qué correos recientemente.

## Deuda Técnica Actual

Milestone v8 (ver `.planning/STATE.md` y `.planning/ROADMAP.md`):

- ✅ **Suite verde** (Fase 31): 3 tests obsoletos por rediseño saneados.
- ✅ **Escalabilidad de Lotes** (Fase 33): archivado/etiquetado troceado en tandas
  de 100 y acotado a 1000/lote; aviso en UI para lotes grandes (ADR-010).
- ✅ **Modularización JS** (Fase 32 Stage A+B): espacio de nombres `App`
  (`static/shared.js`); `API`/`deleted` compartidos vía `App.*`; sin `onclick`
  inline (ADR-011). Seguimiento opcional: Stage C (`activeEmails`/`aiStatus`/`CATS`).

## Criterio de Éxito Actualizado

La herramienta permite:
1.  **Analizar**: Entender el estado técnico del buzón en segundos.
2.  **Organizar**: Archivar y etiquetar masivamente para mantener el Inbox a cero.
3.  **Automatizar**: Que el sistema aprenda de las acciones locales y proponga reglas de Gmail.
4.  **Exportar**: Extraer evidencias técnicas (.eml) de forma segura.
