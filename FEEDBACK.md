# Feedback Técnico y de Producto

> Revisión viva sincronizada el 2026-06-12. Milestone v7.0 completado.
> La suite automatizada contiene **129 pruebas** operativas.

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

- **Escalabilidad de Lotes**: Verificar el rendimiento del servidor ante archivados masivos de más de 200 correos simultáneos.
- **Modularización JS**: Aunque está separado por archivos, algunos módulos siguen teniendo dependencias cruzadas mediante variables globales que podrían encapsularse mejor.

## Criterio de Éxito Actualizado

La herramienta permite:
1.  **Analizar**: Entender el estado técnico del buzón en segundos.
2.  **Organizar**: Archivar y etiquetar masivamente para mantener el Inbox a cero.
3.  **Automatizar**: Que el sistema aprenda de las acciones locales y proponga reglas de Gmail.
4.  **Exportar**: Extraer evidencias técnicas (.eml) de forma segura.
