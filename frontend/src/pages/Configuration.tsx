import type { ImportStatus, DataHealth } from "../types";
import { formatDate } from "../format";

export function Configuration({
  status,
  health,
  onRun,
}: {
  status: ImportStatus | null;
  health: DataHealth | null;
  onRun: () => void;
}) {
  return (
    <>
      <header>
        <p className="eyebrow">Ajustes</p>
        <h1>Configuración</h1>
      </header>
      <section className="card configuration">
        <div>
          <h2>Importación desde Gmail</h2>
          <p>
            {status?.enabled
              ? "La conexión IMAP está configurada y se revisa periódicamente."
              : "Desactivada: configura EMAIL_USERNAME y EMAIL_PASSWORD para activarla."}
          </p>
        </div>
        <span className={status?.enabled ? "status ready" : "status"}>
          {status?.enabled ? "Activa" : "Desactivada"}
        </span>
        <dl>
          <dt>Última revisión</dt>
          <dd>{formatDate(status?.last_run ?? null)}</dd>
          <dt>Última correcta</dt>
          <dd>{formatDate(status?.last_success ?? null)}</dd>
          <dt>Importados en la última revisión</dt>
          <dd>{status?.imported_receipts_last_run ?? 0}</dd>
          <dt>Último error</dt>
          <dd>{status?.last_error ?? "Ninguno"}</dd>
        </dl>
        <button disabled={!status?.enabled} onClick={onRun}>
          Buscar nuevos tickets ahora
        </button>
      </section>
      <section className="card data-health">
        <h2>Salud de los datos</h2>
        {health ? (
          <dl>
            <dt>Tickets</dt>
            <dd>{health.total_receipts}</dd>
            <dt>Productos</dt>
            <dd>{health.total_products}</dd>
            <dt>Sin categoría</dt>
            <dd>{health.uncategorized_products}</dd>
            <dt>Tickets para revisar</dt>
            <dd>{health.receipts_needing_review}</dd>
            <dt>Avisos del parser</dt>
            <dd>{health.parser_warning_count}</dd>
          </dl>
        ) : (
          <p>Cargando resumen…</p>
        )}
        <p className="export-links">
          <a href="/api/export/receipts.csv">Exportar compras</a>
          <a href="/api/export/items.csv">Exportar líneas</a>
          <a href="/api/export/products.csv">Exportar productos</a>
        </p>
      </section>
    </>
  );
}
