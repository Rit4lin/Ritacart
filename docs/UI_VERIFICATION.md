# Verificación del rediseño

La revisión local se realizó con una base SQLite temporal y PDF sintéticos de los fixtures del proyecto. No se montó ni modificó el volumen real `/data`.

- Compilación de producción y pruebas del backend y frontend: véanse los resultados de la Pull Request.
- En navegador: inicio vacío y con datos; importación de PDF sintéticos de Mercadona y Carrefour; detalle de ticket y filtros; búsqueda; selección, nombre y categoría de producto; navegación de las cuatro secciones de análisis; diagnóstico y descarga de los tres CSV. Se comprobó un fallo simulado del resumen y la opción de reintento.
- Revisión visual a 1280 px y 390 px. Se corrigió un desbordamiento horizontal en móvil. Capturas locales realizadas con datos sintéticos.
- Axe ejecutado sobre inicio, compras y análisis de gastos en móvil con reglas etiquetadas WCAG 2.x A/AA y 2.2 AA: sin infracciones automáticas en esos estados. Esto no sustituye pruebas completas con teclado, lector de pantalla, zoom, todos los estados y dispositivos ni garantiza conformidad AA.
- Importación IMAP real, reprocesado y confirmación efectiva de unión no se ejecutaron contra datos reales. Las pruebas existentes cubren los servicios correspondientes en un entorno temporal; conviene revisar estos recorridos manualmente antes de publicar.
- Docker y Unraid: el `Dockerfile`, Compose, backend y parsers no se han modificado. La compilación de la imagen local depende de tener el motor Docker disponible; validar la imagen candidata y el arranque con una copia de `/data` antes de la publicación. No ejecutar dos versiones simultáneamente sobre la misma base SQLite. Mantener una copia de seguridad de la base, archivos WAL/SHM y PDF y conservar el mismo montaje `/data` al actualizar.
- `npm audit` de la instalación original informó de dos vulnerabilidades altas en dependencias del proceso de construcción (`vite` y `source-map-js`); no se han actualizado en este rediseño. El contenedor de producción usa la salida estática, no el servidor de desarrollo de Vite. Evaluar las actualizaciones por separado.
