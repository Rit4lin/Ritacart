import type { ProductSummary, Overview } from "../types";
import { formatMoney, formatDate } from "../format";
import { Metric, TopProducts } from "../components/Common";

export function Home({
  overview,
  topProducts,
  loading,
  error,
  onRetry,
  onShowReceipt,
  onShowProduct,
}: {
  overview: Overview | null;
  topProducts: ProductSummary[];
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  onShowReceipt: (id: number) => void;
  onShowProduct: (id: number) => void;
}) {
  return (
    <>
      <header>
        <p className="eyebrow">Resumen</p>
        <h1>La compra, de un vistazo.</h1>
      </header>
      {loading ? (
        <p role="status">Cargando datos…</p>
      ) : error || !overview ? (
        <section className="card">
          <p>No se ha podido cargar el resumen.</p>
          <button onClick={onRetry}>Reintentar</button>
        </section>
      ) : (
        <>
          <section className="metrics" aria-label="Resumen de gastos">
            <Metric
              label="Gasto total"
              value={formatMoney(overview.total_spend)}
            />
            <Metric label="Compras" value={String(overview.receipt_count)} />
            <Metric
              label="Este mes"
              value={formatMoney(overview.current_month_spend)}
            />
          </section>
          <section className="card latest">
            <div>
              <p className="eyebrow">Última compra</p>
              {overview.latest_receipt ? (
                <>
                  <h2>{formatMoney(overview.latest_receipt.total)}</h2>
                  <p>
                    {formatDate(overview.latest_receipt.purchased_at)} ·{" "}
                    {overview.latest_receipt.item_count} productos
                  </p>
                </>
              ) : (
                <p>Aún no hay tickets importados.</p>
              )}
            </div>
            {overview.latest_receipt && (
              <button
                onClick={() => onShowReceipt(overview.latest_receipt!.id)}
              >
                Ver ticket
              </button>
            )}
          </section>
          {topProducts.length > 0 && (
            <TopProducts
              title="Productos más comprados"
              products={topProducts}
              onSelect={onShowProduct}
            />
          )}
        </>
      )}
    </>
  );
}
