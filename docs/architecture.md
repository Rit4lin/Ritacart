# RitaCart architecture

## Scope

RitaCart is a local-first grocery analytics application. The system imports digital supermarket receipts from email, parses them into structured observations and exposes historical analytics through a web UI.

The architecture should remain intentionally small until real requirements justify additional services.

## Initial deployment model

```text
┌──────────────────────────────────────────────┐
│                 RitaCart Docker              │
│                                              │
│  FastAPI                                     │
│  ├── REST API                                │
│  ├── email importer                          │
│  ├── PDF extraction                         │
│  ├── supermarket parsers                    │
│  └── analytics queries                       │
│                                              │
│  Compiled React frontend                     │
│                                              │
│  /data                                       │
│  ├── ritacart.db                             │
│  └── receipts/                               │
└──────────────────────────────────────────────┘
                 │
                 ▼
            Gmail / IMAP
```

No external database, queue or cache is required for the MVP.

## Suggested source layout

```text
backend/
  app/
    api/
    models/
    schemas/
    services/
    parsers/
      base.py
      mercadona.py
    analytics/
    main.py
  tests/

frontend/
  src/
    components/
    pages/
    charts/
    api/
    types/

docs/

docker/
```

The exact layout may evolve during implementation, but parser and analytics logic should remain separated from HTTP/controller code.

## Core data model

### Store

Represents the supermarket or source chain.

Suggested fields:
- id
- name
- slug

### Receipt

Represents one shopping trip/ticket.

Suggested fields:
- id
- store_id
- purchased_at
- total
- VAT breakdown by rate (taxable base and tax amount when present on the ticket)
- source_message_id
- source_file_hash
- source_filename
- source_pdf_path
- imported_at

`purchased_at` should preserve the local receipt date and time accurately enough to derive weekday/hour analytics.

### Product

Canonical product used for historical analysis.

Suggested fields:
- id
- name
- category_id (optional initially)
- created_at

### ProductAlias

Maps supermarket/raw ticket names to a canonical product.

Suggested fields:
- id
- store_id
- raw_name
- product_id

A unique constraint on `(store_id, raw_name)` is likely appropriate.

### ReceiptItem

One product observation on one receipt.

Suggested fields:
- id
- receipt_id
- product_id (nullable until normalized if necessary)
- raw_name
- quantity
- unit
- unit_price
- price_per_kg
- total_price
- raw_text

Not every field applies to every product. Weighted and unit products must remain distinguishable.

## Import pipeline

```text
1. Poll configured mailbox
2. Filter candidate messages
3. Find PDF attachments
4. Calculate file hash
5. Reject already-imported files
6. Store original PDF
7. Extract embedded text
8. Detect supermarket/parser
9. Parse receipt metadata and lines
10. Persist raw observations
11. Apply known ProductAlias mappings
12. Make receipt immediately available to analytics
```

Importing the same message/file repeatedly must be safe and must not create duplicates.

## Mercadona parser

The first parser should be deterministic and fixture-driven.

It should extract at minimum:
- purchase date
- purchase time
- total
- raw product name
- quantity
- unit/weight where available
- unit price where available
- price per kg where available
- line total

Unknown lines should not silently disappear. Preserve them or report parsing warnings so parser coverage can improve over time.

## Analytics model

Prefer queries derived from receipt/item observations rather than precomputed counters during the MVP.

Initial analytics:
- spend by day/week/month/year
- shopping trips by month
- average basket value
- visits by weekday
- visits by hour
- average interval between visits
- product purchase occasions
- product quantity over time
- product spend over time
- unit price / EUR-per-kg history
- current vs previous price
- minimum/maximum/average observed price

A purchase occasion is not the same as quantity. Buying 6 units in one receipt counts as one purchase occasion and 6 units.

## API direction

Example endpoints, subject to implementation refinement:

```text
GET /api/health
GET /api/receipts
GET /api/receipts/{id}
POST /api/receipts/{id}/reprocess
GET /api/products
GET /api/products/{id}
GET /api/products/{id}/history
GET /api/analytics/overview
GET /api/analytics/spend
GET /api/analytics/shopping-times
POST /api/import/run
```

Do not create endpoints merely for symmetry. Add them as screens/use cases require them.

## Frontend

Initial pages:

```text
Inicio
Compras
Productos
Estadísticas
Configuración
```

The dashboard should emphasize trends and useful comparisons rather than configuration/status widgets.

## Backups

Persistent state should live under `/data` so Unraid or another Docker host can back up one directory.

At minimum:
- SQLite database
- original imported PDFs

SQLite should use safe transaction settings. Backup documentation should account for WAL files if WAL mode is enabled.

## Non-goals for MVP

- public internet exposure
- multi-tenant accounts
- fine-grained permissions
- mobile native apps
- OCR for Mercadona PDFs that already contain text
- AI extraction
- Redis/job queues
- external SQL database
- generic receipt-processing platform
