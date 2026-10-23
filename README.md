# RitaCart 2.0.0

RitaCart analiza automáticamente los tickets digitales del supermercado para convertirlos en un historial útil de compras, productos y precios.

Está pensada para funcionar **en local con Docker**, sin bases de datos externas ni servicios adicionales. Desde la versión **2.0.0** es compatible con **Mercadona** y **Carrefour**. Mercadona admite importación automática por IMAP y manual; Carrefour solo mediante subida manual.

## Qué hace

- Importa automáticamente los PDF de Mercadona recibidos por Gmail/IMAP. Carrefour no se busca ni descarga por correo.
- Permite subir manualmente tickets PDF de Mercadona y Carrefour, incluidos los escaneados con capa OCR.
- Detecta el supermercado por el encabezado, guarda el histórico de compras y evita duplicados (incluido NRF en Carrefour).
- Muestra gasto total, gasto del mes y últimas compras.
- Agrupa productos y permite renombrarlos o unir duplicados.
- Muestra frecuencia de compra, cantidades y evolución de precios.
- Conserva los PDF originales y los datos en una base SQLite local.
- En Carrefour conserva precios originales, descuentos por artículo, cupones globales, subtotales e IVA; las promociones no se convierten en productos.

## Instalar con Docker

La imagen está publicada en GitHub Container Registry:

```text
ghcr.io/rit4lin/ritacart:latest
```

Ejemplo con `docker run`:

```bash
docker run -d \
  --name ritacart \
  -p 8000:8000 \
  -v /ruta/ritacart:/data \
  -e APP_TIMEZONE=Europe/Madrid \
  -e EMAIL_USERNAME=tu-cuenta@gmail.com \
  -e EMAIL_PASSWORD=tu-contraseña-de-aplicacion \
  --restart unless-stopped \
  ghcr.io/rit4lin/ritacart:latest
```

Después abre:

```text
http://IP_DEL_SERVIDOR:8000
```

Todo lo importante queda guardado en `/data`, incluida la base de datos y los PDF. Para hacer una copia de seguridad basta con respaldar ese directorio.

## Importar tickets de Carrefour (solo manual)

En **Compras → Importar PDF** selecciona el ticket digital de Carrefour. RitaCart detecta automáticamente la tienda. No hay conexión con Carrefour, scraping, correo adicional ni importación en segundo plano.

El parser reconoce las líneas con cantidades tipo `2 x (4,05) 8,10`, promociones `DESCUENTO EN 2ª UNIDAD` por código, cupones `DTO. CUPON`, cheques `DTO. CHEQUE AHORRO`, los tipos de IVA y el identificador `NRF`. El precio original por unidad se conserva para observar la evolución de precios; el gasto del producto refleja el descuento de línea y el importe total de la compra incluye los cupones generales.

Algunos artículos de fruta o granel solo presentan un importe en el ticket, sin peso. RitaCart **no calcula ni inventa €/kg** para esos casos: la cantidad `ud` representa el artículo registrado en el ticket y no el peso real. Si el formato no cuadra, mostrará avisos para revisión.

Solo se han verificado directamente los formatos de los tickets Carrefour de **6 y 22 de octubre de 2026**. Otros modelos de Carrefour pueden requerir extender el parser. La subida de PDF sigue limitada a 20 MB y 20 páginas.

## Actualización a 2.0.0

El esquema SQLite se amplía automáticamente al arrancar, manteniendo los tickets de Mercadona existentes. Antes de actualizar el contenedor, haz una copia de seguridad del directorio persistente `/data`, incluyendo la base SQLite y posibles archivos WAL/SHM. No mezcles procesos ejecutando simultáneamente las versiones antigua y nueva sobre el mismo volumen.

**Publicación:** RitaCart 2.0.0 se distribuye mediante `ghcr.io/rit4lin/ritacart:latest` y la etiqueta fija `ghcr.io/rit4lin/ritacart:v2.0.0`. Una vez publicada la imagen, en Unraid selecciona **Docker → Check for Updates**, descarga la actualización y recrea el contenedor **conservando la misma ruta persistente `/data`**. Si tu plantilla utiliza una etiqueta fija anterior, cambia el repositorio a `ghcr.io/rit4lin/ritacart:v2.0.0` para instalarla; con `:latest`, no cambies la plantilla. Comprueba en la aplicación que la versión es 2.0.0 y que el histórico de Mercadona continúa disponible.

## Gmail

Para importar tickets automáticamente, RitaCart revisa por defecto la bandeja de entrada cada 15 minutos y busca mensajes de:

```text
ticket_digital@mail.mercadona.com
```

Con Gmail debes usar una **contraseña de aplicación**, no la contraseña normal de tu cuenta. Necesitas tener activada la verificación en dos pasos de Google.

Variables disponibles:

```text
EMAIL_USERNAME=tu-cuenta@gmail.com
EMAIL_PASSWORD=tu-contraseña-de-aplicacion
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USE_SSL=true
EMAIL_FOLDER=INBOX
EMAIL_RECEIPT_SENDER=ticket_digital@mail.mercadona.com
EMAIL_POLL_INTERVAL_MINUTES=15
```

Si no configuras Gmail, RitaCart arranca igualmente y puedes importar los PDF manualmente desde la interfaz.

### Tickets escaneados

Para un ticket en papel, escanéalo y aplica OCR antes de importarlo. Por ejemplo, en Adobe Acrobat puedes usar **Escanear y OCR → Reconocer texto** y guardar el PDF resultante. Como comprobación rápida, intenta seleccionar texto o buscar `TOTAL` dentro del PDF.

RitaCart no ejecuta OCR dentro del contenedor: extrae la capa de texto ya presente en el PDF, conserva el archivo original y lo procesa con el mismo historial que los tickets recibidos por email. Si el PDF no tiene texto extraíble, mostrará un aviso indicando que debes aplicar OCR. El límite de subida es de 20 MB por ticket.

## Unraid

En **Docker → Add Container** usa:

| Campo | Valor |
| --- | --- |
| Repository | `ghcr.io/rit4lin/ritacart:latest` |
| Network Type | `bridge` |
| Host Port | `8000` |
| Container Port | `8000` |
| Host Path | `/mnt/user/appdata/ritacart/data` |
| Container Path | `/data` |

Añade `EMAIL_USERNAME` y `EMAIL_PASSWORD` como variables de entorno si quieres la importación automática desde Gmail.

La imagen actual se publica para `linux/amd64`.

## Actualizar

Descarga la última imagen y recrea el contenedor conservando el mismo volumen `/data`.

En Unraid basta con usar **Check for Updates** sobre el contenedor.

## Seguridad

RitaCart está diseñada para utilizarse dentro de una red privada y actualmente no tiene sistema de autenticación. **No expongas el puerto 8000 directamente a Internet.**

## Desarrollo

La documentación técnica y las decisiones de arquitectura están en [`docs/architecture.md`](docs/architecture.md).