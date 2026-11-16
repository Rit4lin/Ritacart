import type { ProductSummary, SearchResults } from "../types";
import { formatMoney, formatQuantity, formatDate } from "../format";

export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <article className="metric">
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

export function TopProducts({
  title,
  products,
  onSelect,
}: {
  title: string;
  products: ProductSummary[];
  onSelect: (id: number) => void;
}) {
  return (
    <section className="card top-products">
      <h2>{title}</h2>
      {products.length ? (
        <ol>
          {products.map((product, index) => (
            <li key={product.id}>
              <button onClick={() => onSelect(product.id)}>
                <span>
                  <b>{index + 1}</b>
                  <strong>{product.name}</strong>
                </span>
                <small>
                  {product.purchase_count} compras · cantidad{" "}
                  {formatQuantity(product.total_quantity)}
                </small>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="empty">Aún no hay suficientes datos.</p>
      )}
    </section>
  );
}

export function SearchPanel({
  results,
  onProduct,
  onReceipt,
}: {
  results: SearchResults;
  onProduct: (id: number) => void;
  onReceipt: (id: number) => void;
}) {
  if (!results.products.length && !results.receipts.length)
    return (
      <div className="search-results">
        <p>Sin resultados.</p>
      </div>
    );
  return (
    <div className="search-results" role="status">
      {results.products.length > 0 && (
        <section>
          <strong>Productos</strong>
          {results.products.map((product) => (
            <button key={product.id} onClick={() => onProduct(product.id)}>
              {product.name}
            </button>
          ))}
        </section>
      )}
      {results.receipts.length > 0 && (
        <section>
          <strong>Compras</strong>
          {results.receipts.map((receipt) => (
            <button key={receipt.id} onClick={() => onReceipt(receipt.id)}>
              {formatDate(receipt.purchased_at)} · {receipt.store} ·{" "}
              {formatMoney(receipt.total)}
            </button>
          ))}
        </section>
      )}
    </div>
  );
}
