# RitaCart

RitaCart es una aplicación local para analizar tickets de compra recibidos por correo electrónico.

La idea es sencilla: importar automáticamente los tickets digitales del supermercado, extraer sus datos y convertirlos en un histórico útil para entender cuánto gastamos, qué compramos, cómo cambian los precios y cuáles son nuestros hábitos de compra.

## Objetivo

RitaCart no pretende ser un gestor de gastos general ni una plataforma multiusuario. Está pensada para ejecutarse en una red local, principalmente mediante Docker, con una instalación pequeña y fácil de mantener.

El primer supermercado soportado será **Mercadona**. La arquitectura permitirá añadir otros parsers más adelante, por ejemplo Carrefour, sin mezclar su lógica con la de Mercadona.

## Qué queremos analizar

- Gasto total por semana, mes y año.
- Evolución del gasto a lo largo del tiempo.
- Histórico de precios por producto.
- Incrementos y descensos de precio.
- Frecuencia con la que se compra cada producto.
- Cantidades compradas por periodo.
- Productos más habituales.
- Días de la semana en los que solemos comprar.
- Horas habituales de compra.
- Número de visitas al supermercado.
- Tiempo medio entre compras.
- Comparaciones entre meses y años.

## Flujo previsto

```text
Correo electrónico
       │
       ▼
Ticket PDF
       │
       ▼
Extracción de texto
       │
       ▼
Parser específico del supermercado
       │
       ▼
Normalización de productos y precios
       │
       ▼
SQLite
       │
       ▼
Dashboard y gráficas
```

Los tickets digitales de Mercadona contienen texto, por lo que el objetivo inicial es procesarlos de forma determinista sin OCR ni modelos de IA.

## Stack previsto

### Backend

- Python 3.13
- FastAPI
- SQLAlchemy
- PyMuPDF para extracción de texto de PDF

### Frontend

- TypeScript
- React
- Vite
- Tailwind CSS

### Datos

- SQLite

### Despliegue

- Docker
- Un único contenedor para la aplicación siempre que sea razonable
- Volumen persistente `/data`

El objetivo es poder ejecutarla fácilmente en Unraid u otro host Docker sin depender de Redis, PostgreSQL, MySQL u otros servicios externos.

## Modelo conceptual inicial

RitaCart distinguirá entre el ticket original y el producto normalizado.

```text
Receipt
 └── ReceiptItem
       └── ProductAlias
             └── Product
```

Esto permite conservar exactamente lo que aparecía en el ticket y, al mismo tiempo, agrupar variantes del nombre de un mismo producto para hacer análisis históricos.

Para precios y cantidades se evitarán números de coma flotante cuando puedan provocar errores de precisión. Los datos monetarios se tratarán como valores decimales.

## Principios del proyecto

- Local-first.
- Sin autenticación compleja mientras la instalación permanezca en una red privada.
- Sin permisos y roles innecesarios.
- Sin OCR si el documento ya contiene texto utilizable.
- Sin IA para tareas que puedan resolverse de forma determinista.
- Mantener siempre el PDF y los valores originales como evidencia de la importación.
- Evitar duplicados usando identificadores del correo y hashes de los archivos.
- Priorizar una arquitectura pequeña y comprensible frente a una plataforma genérica.

## MVP

La primera versión útil deberá poder:

1. Detectar automáticamente nuevos tickets de Mercadona recibidos por email.
2. Descargar y almacenar el PDF.
3. Extraer fecha, hora, total y líneas de producto.
4. Guardar productos, cantidades y precios en SQLite.
5. Evitar importar dos veces el mismo ticket.
6. Mostrar el histórico de compras.
7. Mostrar gasto mensual y anual.
8. Mostrar evolución de precios por producto.
9. Mostrar cuándo solemos hacer la compra por día de la semana y hora.

## Estado

RitaCart importa tickets digitales de Mercadona desde Gmail/IMAP o mediante un
PDF cargado manualmente. Conserva el PDF original, el texto/líneas originales y
los datos normalizados en SQLite. No incluye autenticación, OCR ni analítica
avanzada.

## Arranque

Se necesita Docker Compose. Desde la raíz del repositorio:

```bash
docker compose up --build
```

Abre `http://localhost:8000`. El directorio local `./data` se monta como
`/data` en el contenedor y contiene la base SQLite (`ritacart.db`) y los PDFs
originales (`receipts/`).

## Preparar otro PC para desarrollo

El repositorio incluye `AGENTS.md`, la arquitectura y todas las dependencias
declaradas; no hace falta copiar archivos generados, `.venv`, `node_modules`,
`data/` ni `.env`.

```bash
git clone https://github.com/Rit4lin/Ritacart.git
cd Ritacart
copy .env.example .env
```

Instala Python 3.13 o posterior, Node.js 22 o posterior y Docker Desktop. Para
desarrollo local, crea el entorno Python y ejecuta ambos procesos:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite publica la interfaz en `http://localhost:5173` y redirige `/api` a
FastAPI en `http://localhost:8000`. Para validar antes de trabajar, ejecuta
`cd backend; ..\.venv\Scripts\python -m pytest tests -q` y
`cd frontend; npm run build`.

## Desplegar en Unraid desde GHCR

Al fusionar cambios en `main`, GitHub Actions publica la imagen multi-arquitectura
en `ghcr.io/rit4lin/ritacart:latest`. Las etiquetas Git `v*` también generan una
imagen versionada. La publicación usa el `GITHUB_TOKEN` de Actions; no requiere
guardar un token de registro en el repositorio.

Después de la primera publicación, comprueba en GitHub, en la sección
**Packages**, que `ritacart` sea pública. Así Unraid puede descargarla sin
credenciales de GitHub.

En la GUI de Unraid, ve a **Docker → Add Container** y crea esta plantilla:

| Campo | Valor |
| --- | --- |
| Name | `ritacart` |
| Repository | `ghcr.io/rit4lin/ritacart:latest` |
| Network Type | `bridge` |
| Host Port | `8000` |
| Container Port | `8000` |
| Host Path | `/mnt/user/appdata/ritacart/data` |
| Container Path | `/data` |
| Access Mode | `Read/Write` |

Añade estas variables de entorno desde la misma plantilla:

```text
APP_DATA_DIR=/data
DATABASE_URL=sqlite:////data/ritacart.db
APP_TIMEZONE=Europe/Madrid
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USE_SSL=true
EMAIL_USERNAME=tu-cuenta@gmail.com
EMAIL_PASSWORD=tu-contraseña-de-aplicación
EMAIL_FOLDER=INBOX
EMAIL_RECEIPT_SENDER=ticket_digital@mail.mercadona.com
EMAIL_POLL_INTERVAL_MINUTES=15
```

Activa **Auto Start** y abre `http://IP_DE_UNRAID:8000`. Para actualizar,
usa **Docker → Check for Updates** y aplica la actualización de `ritacart`;
el volumen `/mnt/user/appdata/ritacart/data` conserva la base de datos y los
PDFs. No expongas el puerto 8000 a Internet: RitaCart no tiene autenticación.

## Configurar Gmail con Docker Compose

1. Copia `.env.example` como `.env` junto a `docker-compose.yml`.
2. Rellena `EMAIL_USERNAME` y `EMAIL_PASSWORD`. Para Gmail, utiliza una
   [contraseña de aplicación](https://support.google.com/accounts/answer/185833)
   con la verificación en dos pasos activada; no uses tu contraseña habitual.
3. Conserva `EMAIL_USE_SSL=true`, configura el remitente esperado y ajusta el
   intervalo si hace falta. El valor predeterminado busca
   `ticket_digital@mail.mercadona.com` cada 15 minutos.
4. Ejecuta `docker compose up --build -d`.

En Unraid, usa el mismo directorio de aplicación como contexto de Compose y
guarda estas variables como secretos/configuración del despliegue, nunca en la
imagen o en Git. Si `EMAIL_USERNAME` o `EMAIL_PASSWORD` están vacíos, RitaCart
arranca con normalidad y la importación automática queda desactivada. La página
Configuración lo indica sin exponer la contraseña.

## API inicial

- `GET /api/health`
- `GET /api/overview`
- `GET /api/receipts`
- `GET /api/receipts/{id}`
- `POST /api/receipts/import` (campo multipart `file`)
- `GET /api/import/status`
- `POST /api/import/run`

## Limitaciones actuales del parser

El parser reconoce de forma determinista líneas unitarias y pesadas habituales
de Mercadona. Conserva avisos para líneas que no pueda interpretar, pero otros
formatos de ticket, descuentos complejos y cambios de maquetación requerirán
nuevas fixtures y reglas de parser antes de soportarse.
