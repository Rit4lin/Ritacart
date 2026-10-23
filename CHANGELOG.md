# Changelog

## 2.0.0 (propuesta de versión, pendiente de publicar)

**Nueva compatibilidad:** tickets PDF de Carrefour, importados solo manualmente desde la pantalla Compras. Los tickets Mercadona mantienen su importación por IMAP y manual.

### Funcionalidad
- Detector de supermercado por cabecera PDF y parser Carrefour independiente.
- Lectura de fecha, líneas de artículos, cantidades, precio, subtotal, total e IVA.
- Descuentos por segunda unidad asociados al artículo a través de los códigos promocionales.
- Registro diferenciado de importes originales, descuentos por línea y precios netos.
- Cupones y cheques a nivel de compra sin crear productos ficticios.
- Detección de duplicados por SHA-256, referencia NRF (Carrefour) y firma semántica dependiente de tienda.
- Reprocesamiento con el parser de la tienda original.
- Interfaz de Compras con tienda, descuentos y desglose de pago.
- Migraciones SQLite solo aditivas con preservación de los registros existentes.

### Compatibilidad y limitaciones
- Importación automática por correo: solo Mercadona.
- Carrefour: soportados y contrastados los dos modelos de ticket probados (06/10/2026 y 22/10/2026).
- Artículos a granel sin peso: no se infiere €/kg.
- Los cupones globales afectan al total de compra, no se prorratean automáticamente entre productos ni categorías.
- Antes de actualizar un contenedor persistente, es recomendable respaldar /data.

### Verificación
- Pruebas del parser con dos casos completos sanitizados, descuentos y aritmética.
- Pruebas de API y regresión de Mercadona; comprobaciones de compilación TypeScript y frontend mediante GitHub Actions.
- **No se publica imagen Docker, etiqueta de versión ni release con esta PR.** La publicación y el despliegue requieren un paso posterior.
