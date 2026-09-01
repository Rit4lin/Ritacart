# AGENTS.md

## Project goal

RitaCart is a local-first household grocery analytics application. Its primary job is to import supermarket receipt PDFs received by email and turn them into a clean historical dataset for spending, product price and shopping-habit analysis.

The first supported source is Mercadona digital receipts. Other supermarkets may be added later through isolated parser modules.

## Product constraints

Keep the product intentionally small.

- This is not a generic expense manager.
- This is not a SaaS product.
- This is not initially multi-tenant or multi-user.
- Do not add complex authentication, RBAC or permission systems unless explicitly requested.
- Do not introduce Redis, Celery, PostgreSQL, MySQL, Kafka or other infrastructure unless there is a demonstrated need.
- Prefer a single Docker container and a persistent `/data` volume.
- SQLite is the default database.
- The application is expected to run on a private LAN, commonly on Unraid.

## Planned stack

Backend:
- Python 3.13
- FastAPI
- SQLAlchemy
- PyMuPDF

Frontend:
- TypeScript
- React
- Vite
- Tailwind CSS

Database:
- SQLite

Deployment:
- Docker

## Architecture principles

### Deterministic parsing first

Mercadona digital PDFs contain embedded text. Parse that text directly.

Do not add OCR or an LLM to the primary Mercadona import path unless real sample receipts prove deterministic parsing insufficient.

Store parser implementations separately, for example:

```text
backend/app/parsers/
├── base.py
├── mercadona.py
└── carrefour.py
```

### Preserve raw evidence

Never make normalized data the only copy of imported information.

Preserve:
- original PDF or its durable local path
- message identifier where available
- file hash
- original receipt line text
- original extracted values

Normalization must be reversible/auditable from the raw receipt data.

### Product identity

Do not assume the raw receipt name is the canonical product name.

Prefer a model equivalent to:

```text
Product
ProductAlias(store_id, raw_name, product_id)
Receipt
ReceiptItem(receipt_id, product_id, raw_name, quantity, unit, unit_price, total_price, ...)
```

Do not over-normalize products prematurely. A concrete supermarket product should remain distinguishable when that distinction matters for price history.

### Quantities and prices

Model unit products and weighted products correctly.

Examples:

```text
2 LIMÓN ZERO 2L 0,95 1,90
```

means quantity 2, unit price 0.95 and line total 1.90.

```text
PERA CONFERENCIA
0,490 kg 2,75 €/kg 1,35
```

means quantity 0.490 kg, unit price 2.75 EUR/kg and line total 1.35 EUR.

Do not treat line total as product unit price.

Use Decimal-compatible database/application types for money and measured quantities where precision matters. Do not use binary floating point for monetary calculations.

### Dates and time

Receipt date and time are first-class analytics fields.

Default deployment timezone is `Europe/Madrid`, configurable through environment variables. Store enough information to produce correct local day-of-week and hour-of-day analytics.

### Duplicate prevention

Imports must be idempotent.

Use stable email identifiers when possible and a cryptographic PDF hash as a second line of defence. Re-running the importer must not duplicate an existing receipt.

## MVP analytics

Prioritize these views before adding broader features:

- spend by month/year
- number of shopping trips
- average basket value
- product purchase frequency
- quantity purchased over time
- product price history
- price increase/decrease
- most frequently purchased products
- shopping trips by weekday
- shopping trips by hour
- average days between shopping trips

Derived metrics should generally be computed from exact receipt observations rather than stored redundantly.

## Email ingestion

Email credentials must never be committed.

Use environment variables or Docker secrets/configuration for credentials. The initial implementation may use IMAP if it keeps deployment simple. Gmail-specific APIs should only be introduced if they solve a concrete limitation.

The importer should filter narrowly for expected receipt senders/attachments and should fail safely when encountering an unknown format.

## Testing priorities

This project does not need an elaborate E2E infrastructure initially.

Prioritize:
1. parser tests using anonymized/synthetic receipt text fixtures
2. database model and migration tests
3. duplicate-import tests
4. analytics calculation tests
5. API tests for critical endpoints

Every parser bug fixed from a real receipt should ideally gain a regression fixture/test.

## Frontend guidance

The UI should be data-first and compact. Prioritize useful charts and clear comparisons over administrative screens.

Initial navigation should remain small, approximately:

```text
Inicio
Compras
Productos
Estadísticas
Configuración
```

Do not introduce a large component framework without need. Prefer accessible reusable components and keep the dependency count modest.

## Docker guidance

Use a multi-stage build so Node/build tooling does not remain in the runtime image.

The production image should contain only what is required to:
- run the Python application
- serve the compiled frontend
- read PDFs
- persist data under `/data`

Avoid build-essential, compilers, Node.js and package caches in the final image unless they are genuinely required at runtime.

## Security scope

The intended deployment is local/private, but basic security hygiene still applies:

- no secrets in Git
- validate uploaded/imported files
- avoid arbitrary filesystem access
- parameterize database queries through the ORM
- do not trust email attachment names
- keep dependencies patched

Do not build an enterprise authorization model unless requirements change.

## Development style

Favor straightforward code over abstractions created for hypothetical future scale.

Before adding a service, dependency, queue, cache, framework or architectural layer, explain what concrete problem it solves for RitaCart.

Keep commits focused and update this document or README when architectural decisions materially change.
