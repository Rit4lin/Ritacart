import { useEffect, useState } from "react";
import type {
  ProductSummary,
  Category,
  PriceSummary,
  ProductAnalytics,
} from "../types";
import { months, formatMoney, formatQuantity, formatDate } from "../format";
import { BarChart, LineChart } from "../components/Charts";
import { Metric } from "../components/Common";

export function Products({
  products,
  state,
  onRetry,
  categories,
  selected,
  onSelect,
  onMerge,
  onRename,
  onCategoryChange,
}: {
  products: ProductSummary[];
  state: "loading" | "ready" | "error";
  onRetry: () => void;
  categories: Category[];
  selected: ProductAnalytics | null;
  onSelect: (id: number) => void;
  onMerge: (sourceId: number, targetId: number) => void;
  onRename: (id: number, name: string) => void;
  onCategoryChange: (id: number, categoryId: number | null) => void;
}) {
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false);
  const visibleProducts = uncategorizedOnly
    ? products.filter((product) => !product.category)
    : products;
  return (
    <>
      <header>
        <p className="eyebrow">Catálogo</p>
        <h1>Productos</h1>
      </header>
      <div className="product-layout">
        <section className="card product-list">
          <label className="product-filter">
            <input
              type="checkbox"
              checked={uncategorizedOnly}
              onChange={(event) => setUncategorizedOnly(event.target.checked)}
            />{" "}
            Solo sin categoría
          </label>
          {state === "loading" ? (
            <p className="empty" role="status">
              Cargando productos…
            </p>
          ) : state === "error" ? (
            <div className="empty">
              <p>No se han podido cargar los productos.</p>
              <button onClick={onRetry}>Reintentar</button>
            </div>
          ) : visibleProducts.length ? (
            visibleProducts.map((product) => (
              <button
                className={
                  selected?.id === product.id
                    ? "product-row selected"
                    : "product-row"
                }
                key={product.id}
                onClick={() => onSelect(product.id)}
              >
                <strong>{product.name}</strong>
                <small>
                  {product.category?.name ?? "Sin categoría"} ·{" "}
                  {product.purchase_count} compras · cantidad{" "}
                  {formatQuantity(product.total_quantity)}
                </small>
              </button>
            ))
          ) : (
            <p className="empty">No hay productos que mostrar.</p>
          )}
        </section>
        <ProductDetail
          product={selected}
          products={products}
          categories={categories}
          onMerge={onMerge}
          onRename={onRename}
          onCategoryChange={onCategoryChange}
        />
      </div>
    </>
  );
}

export function ProductDetail({
  product,
  products,
  categories,
  onMerge,
  onRename,
  onCategoryChange,
}: {
  product: ProductAnalytics | null;
  products: ProductSummary[];
  categories: Category[];
  onMerge: (sourceId: number, targetId: number) => void;
  onRename: (id: number, name: string) => void;
  onCategoryChange: (id: number, categoryId: number | null) => void;
}) {
  if (!product)
    return (
      <section className="card detail empty">
        Selecciona un producto para consultar su historial.
      </section>
    );
  return (
    <ProductDashboard
      product={product}
      products={products}
      categories={categories}
      onMerge={onMerge}
      onRename={onRename}
      onCategoryChange={onCategoryChange}
    />
  );
}

export function ProductDashboard({
  product,
  products,
  categories,
  onMerge,
  onRename,
  onCategoryChange,
}: {
  product: ProductAnalytics;
  products: ProductSummary[];
  categories: Category[];
  onMerge: (sourceId: number, targetId: number) => void;
  onRename: (id: number, name: string) => void;
  onCategoryChange: (id: number, categoryId: number | null) => void;
}) {
  const [name, setName] = useState(product.name);
  useEffect(() => setName(product.name), [product.id, product.name]);
  const priceSeries = new Map<string, ProductAnalytics["price_history"]>();
  product.price_history.forEach((point) =>
    priceSeries.set(point.price_unit, [
      ...(priceSeries.get(point.price_unit) ?? []),
      point,
    ]),
  );
  return (
    <section className="product-detail">
      <section className="card">
        <div className="detail-title">
          <div>
            <p className="eyebrow">Producto</p>
            <h2>{product.name}</h2>
            <p>
              {product.purchase_count} compras · cantidad acumulada{" "}
              {formatQuantity(product.total_quantity)}
            </p>
          </div>
        </div>
        <label className="category-control">
          Categoría
          <select
            value={product.category?.id ?? ""}
            onChange={(event) =>
              onCategoryChange(
                product.id,
                event.target.value ? Number(event.target.value) : null,
              )
            }
          >
            <option value="">Sin categoría</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <section className="product-metrics" aria-label="Resumen del producto">
          <Metric
            label="Gasto total"
            value={formatMoney(product.total_spend)}
          />
          <Metric label="Comprado" value={`${product.purchase_count} veces`} />
          <Metric
            label="Frecuencia"
            value={
              product.average_days_between_purchases
                ? `Cada ${product.average_days_between_purchases.replace(".", ",")} días`
                : "Sin histórico suficiente"
            }
          />
          <Metric
            label="Primera compra"
            value={formatDate(product.first_purchased_at)}
          />
          <Metric
            label="Última compra"
            value={formatDate(product.last_purchased_at)}
          />
        </section>
        {product.price_summary.length ? (
          <section className="price-summaries">
            {product.price_summary.map((summary) => (
              <PriceSummaryCard key={summary.price_unit} summary={summary} />
            ))}
          </section>
        ) : (
          <p className="empty">No hay precios observados para este producto.</p>
        )}
        <form
          className="rename-control"
          onSubmit={(event) => {
            event.preventDefault();
            if (name.trim() && name.trim() !== product.name)
              onRename(product.id, name);
          }}
        >
          <label htmlFor="product-name">Nombre mostrado</label>
          <div>
            <input
              id="product-name"
              value={name}
              maxLength={255}
              onChange={(event) => setName(event.target.value)}
            />
            <button
              type="submit"
              disabled={!name.trim() || name.trim() === product.name}
            >
              Guardar nombre
            </button>
          </div>
          <small>
            Los próximos tickets con cualquiera de estos nombres se asociarán a
            este producto.
          </small>
        </form>
        <p className="alias-list">
          Nombres del ticket: {product.aliases.join(" · ")}
        </p>
        <label className="merge-control">
          Unir este producto con
          <select
            defaultValue=""
            onChange={(event) => {
              const targetId = Number(event.target.value);
              if (
                targetId &&
                window.confirm(
                  `Se unirá ${product.name} con ${products.find((candidate) => candidate.id === targetId)?.name ?? "el producto seleccionado"}. Esta acción cambia el catálogo y su historial. ¿Continuar?`,
                )
              )
                onMerge(product.id, targetId);
              event.currentTarget.value = "";
            }}
          >
            <option value="">Selecciona un producto…</option>
            {products
              .filter((candidate) => candidate.id !== product.id)
              .map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.name}
                </option>
              ))}
          </select>
        </label>
      </section>
      <section className="chart-grid">
        <BarChart
          title="Compras por mes"
          subtitle="Tickets que contienen el producto"
          points={product.monthly_purchases.map((point) => ({
            label: point.month,
            value: point.purchase_count,
            detail: `cantidad ${formatQuantity(point.total_quantity)}`,
          }))}
        />
        <BarChart
          title="Gasto por mes"
          subtitle="Importe observado en tickets"
          points={product.monthly_spend.map((point) => ({
            label: point.month,
            value: Number(point.total_spend),
            detail: formatMoney(point.total_spend),
          }))}
        />
        <BarChart
          title="Patrón por temporada"
          subtitle="Compras agrupadas por mes del año"
          points={product.seasonal_purchases.map((point) => ({
            label: months[point.month - 1],
            value: point.purchase_count,
          }))}
        />
        {[...priceSeries.entries()].map(([unit, points]) => (
          <LineChart
            key={unit}
            title={`Evolución de precio (${unit})`}
            subtitle="Máximo observado cada día de compra"
            points={points.map((point) => ({
              label: point.date,
              value: Number(point.price),
            }))}
          />
        ))}
      </section>
    </section>
  );
}

export function PriceSummaryCard({ summary }: { summary: PriceSummary }) {
  const difference = Number(summary.change_absolute ?? 0);
  const signal = difference > 0 ? "↑" : difference < 0 ? "↓" : "=";
  const change =
    summary.change_percent === null
      ? "Sin histórico suficiente"
      : `${signal} ${Number(summary.change_percent).toLocaleString("es-ES", { maximumFractionDigits: 1 })} %`;
  return (
    <article className="price-summary">
      <h3>{summary.price_unit}</h3>
      <dl>
        <dt>Actual</dt>
        <dd>{formatMoney(summary.current_price)}</dd>
        <dt>Anterior</dt>
        <dd>
          {summary.previous_price
            ? formatMoney(summary.previous_price)
            : "Sin histórico suficiente"}
        </dd>
        <dt>Variación</dt>
        <dd aria-label={`Variación ${change}`}>{change}</dd>
        <dt>Mínimo</dt>
        <dd>{formatMoney(summary.min_price)}</dd>
        <dt>Máximo</dt>
        <dd>{formatMoney(summary.max_price)}</dd>
        <dt>Media</dt>
        <dd>{formatMoney(summary.average_price)}</dd>
      </dl>
    </article>
  );
}
