# RitaCart

RitaCart analiza automáticamente los tickets digitales del supermercado para convertirlos en un historial útil de compras, productos y precios.

Está pensada para funcionar **en local con Docker**, sin bases de datos externas ni servicios adicionales. Actualmente está enfocada en los tickets digitales de **Mercadona**.

## Qué hace

- Importa automáticamente los PDF recibidos por Gmail/IMAP.
- También permite subir un ticket PDF manualmente.
- Guarda el histórico de compras y evita duplicados.
- Muestra gasto total, gasto del mes y últimas compras.
- Agrupa productos y permite renombrarlos o unir duplicados.
- Muestra frecuencia de compra, cantidades y evolución de precios.
- Conserva los PDF originales y los datos en una base SQLite local.

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