# Plan de Testeo Humano: Gestor de Inteligencia Gmail

Este documento guía al usuario a través de las pruebas manuales para verificar que todas las prestaciones de la aplicación funcionan según lo esperado.

## 1. Configuración y Arranque
- [ ] **Modo Estándar:** Ejecuta `.venv/bin/python server.py`. Verifica que se abre el navegador en `localhost:8765`.
- [ ] **Modo Headless:** Ejecuta `HEADLESS=1 .venv/bin/python server.py`. Verifica que no abre navegador y muestra la URL en consola.
- [ ] **Carga de .env:** Cambia el `PORT` en `.env` a `8888`, reinicia y verifica el cambio.

## 2. Búsqueda e Inteligencia
- [ ] **Búsqueda por Remitente:** Busca `paypal.com`. Verifica que aparecen los correos y tienen categoría "💰 Monetario".
- [ ] **Búsqueda por Fechas:** Limpia el remitente y busca un rango de 3 días. Verifica que aparecen correos de distintos remitentes.
- [ ] **Búsqueda Literal:** Busca la palabra "factura" combinada con fechas. Verifica la precisión.

## 3. Gestión de Gmail (Acciones Reales)
- [ ] **Archivado:** Selecciona un correo y pulsa "📦 Archivar".
    - [ ] Verifica en la app que desaparece de la vista y va a "Ocultos".
    - [ ] Verifica en Gmail Web que el correo ya no está en la bandeja de entrada (Recibidos).
- [ ] **Etiquetado:** Selecciona un correo y pulsa "🏷 Etiquetar".
    - [ ] Elige una etiqueta existente. Verifica en Gmail Web.
    - [ ] Crea una etiqueta nueva (ej. `TEST_APP`) usando el buscador dinámico. Verifica en Gmail Web que se ha creado.

## 4. Automatización
- [ ] **Regla Auto-Label:** Crea una regla para un remitente con "Aplicar etiqueta automáticamente". Busca ese remitente y verifica que los correos se etiquetan solos.
- [ ] **Regla Auto-Archive:** Crea una regla con "Archivar automáticamente". Busca el remitente y verifica que los correos no llegan a aparecer en la bandeja de la app (van directos a ocultos).

## 5. Sugerencias IA (Opcional)
- [ ] **Activación:** Activa el toggle de IA en el panel de reglas.
- [ ] **Aprendizaje:** Oculta 5 correos de un remitente nuevo.
- [ ] **Sugerencia:** Pulsa "Sugerir reglas ahora". Verifica que la IA propone una regla coherente.
- [ ] **Aplicación:** Pulsa "Aplicar" en la sugerencia y guarda la regla.

## 6. Exportación y Lector Integrado
- [ ] **Exportación EML:** Selecciona un correo y pulsa "✉ Exportar EML".
    - [ ] Verifica que aparece en el panel "📦 Exportaciones locales".
    - [ ] Verifica que el archivo está físicamente en la carpeta `/exports` del proyecto.
- [ ] **Visor Interno:** Haz clic en el correo exportado desde la lista.
    - [ ] Verifica que se abre el visor interno (sin abrir Apple Mail).
    - [ ] Comprueba que se ve el remitente, fecha, asunto y el cuerpo (HTML/Texto).
- [ ] **Exportación ZIP:** Selecciona 3 correos y exporta. Verifica que el `.zip` se crea en `/exports`.

## 7. Integración con el Sistema (Servicios)
- [ ] **Abrir archivo externo:** Desde la terminal, ejecuta:
    `.venv/bin/python server.py --open "/ruta/a/cualquier/archivo.eml"`
    - [ ] Verifica que la app se abre (o usa la instancia abierta) y muestra ese correo específico en el visor.

## 8. Seguridad y Mantenimiento
- [ ] **Borrado Permanente:** Habilita `ENABLE_PERMANENT_DELETE=1`.
    - [ ] Autoriza en la bandeja de ocultos.
    - [ ] Borra un correo de prueba. Verifica que desaparece de Gmail (ni en papelera).
- [ ] **Revocación:** Pulsa "Revocar autorización" y verifica que el acceso destructivo se cierra.
