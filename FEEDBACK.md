# Feedback Técnico y de Producto

> Revisión viva sincronizada el 2026-06-11. Los milestones v1 a v5 están
> completados y la suite automatizada contiene 121 pruebas.

## Sinopsis

La herramienta funciona como panel local de inteligencia operativa sobre Gmail y cierra el ciclo de ocultos: revisión paginada, restauración, limpieza de huérfanos y borrado permanente bajo una frontera destructiva aislada y revocable.

## Problemas Iniciales Resueltos

### 1. CORS abierto en una API con acceso a Gmail

Resuelto: no se expone CORS abierto, la UI usa rutas relativas y el servidor rechaza explícitamente cabeceras `Host` no locales y orígenes externos.

### 2. Estado OAuth mezclado con estado de salud

Resuelto: `/api/status` usa `gmail_status()` y no inicia OAuth.

### 3. Render HTML vulnerable a entradas no confiables

Mitigado: los datos Gmail y entradas dinámicas pasan por escape; permanecen algunos `innerHTML` estructurales controlados.

### 4. Sin persistencia local

Resuelto: `storage.py` persiste fuentes, ocultados y preferencias en `app_state.json` mediante escritura atómica.

### 5. Autorización destructiva persistente sin salida explícita

Resuelto: el token destructivo válido o renovable se reutiliza entre sesiones, pero puede revocarse desde la UI o `POST /api/delete-revoke`.

### 6. Huérfanos confundidos con fallos temporales

Resuelto: Gmail `not found` se clasifica como huérfano, se purga de la referencia oculta y de la sesión, y no reaparece tras recargar porque se retiró el pool estático `BASE`.

## Mejoras Funcionales Recomendadas

- Ampliar reglas configurables con reordenación y operadores más avanzados.
- Histórico de búsquedas y fuentes.
- Detección de duplicados y agrupación por conversación/asunto.
- Informes especializados de costes, renovaciones, SSL, backups y seguridad.
- Fuente de verdad única para eliminar de forma persistente mensajes base que ya no existen en Gmail.

## Deuda Técnica Conocida

- Unificar las reglas base de categorías y severidad duplicadas entre `classifier.py` y `static/app.js`.
- Mantener Gmail como única fuente de verdad para los mensajes cargados.
- Mantener bajo revisión los `innerHTML` estructurales del frontend cuando se añadan nuevas entradas dinámicas.

## Arquitectura Actual

Mantener un backend Python local, pero separar responsabilidades:

- `server.py`: arranque HTTP y rutas.
- `gmail_client.py`: OAuth y Gmail API.
- `storage.py`: estado local JSON normalizado.
- `classifier.py`: reglas de categorías, severidad y agrupación.
- `destructive_gmail.py`: autorización destructiva separada, revocación y borrado permanente por lotes.
- `index.html`: estructura de UI; estilos y comportamiento viven en activos estáticos separados.

## Criterio de Éxito

La herramienta debe permitir abrirla por la mañana y responder en menos de un minuto:

- qué ha pasado,
- qué requiere acción,
- qué puede ignorarse,
- qué debe documentarse o exportarse.
