import { useEffect, useState } from "react";
import type {
  ProductSummary,
  StatisticsRange,
  Statistics,
  Comparison,
  InsightProduct,
  ProductInsights,
  CategoryAnalytics,
  HabitProduct,
  BasketInsights,
} from "../types";
import {
  formatMoney,
  formatQuantity,
  formatDate,
  formatMonth,
} from "../format";
import { BarChart, LineChart } from "../components/Charts";
import { Metric, TopProducts } from "../components/Common";

export function Habits({
  data,
  error,
  onShowProduct,
}: {
  data: BasketInsights | null;
  error: boolean;
  onShowProduct: (id: number) => void;
}) {
  if (!data)
    return (
      <>
        <header className="section-header">
          <h2>Hábitos de compra</h2>
          <p>Un vistazo a tus patrones y a tu cesta habitual.</p>
        </header>
        <p role="status">
          {error
            ? "No se han podido cargar los hábitos. Vuelve a seleccionar esta sección para reintentar."
            : "Cargando hábitos…"}
        </p>
      </>
    );
  const inflation = data.basket.personal_inflation;
  return (
    <>
      <header className="section-header">
        <h2>Hábitos de compra</h2>
        <p>Un vistazo a tus patrones y a tu cesta habitual.</p>
      </header>
      <section className="habit-metrics">
        <Metric
          label="Cesta habitual"
          value={`${data.basket.items.length} productos`}
        />
        <Metric
          label="Coste actual"
          value={formatMoney(data.basket.current_basket_cost)}
        />
        <Metric
          label="Inflación personal"
          value={
            inflation
              ? `${Number(inflation.change_percent).toLocaleString("es-ES", { maximumFractionDigits: 1 })} %`
              : "Sin datos suficientes"
          }
        />
      </section>
      <section className="chart-grid">
        <section className="card habit-basket">
          <h2>Cesta habitual</h2>
          <p>Estimación con tu cantidad típica y el último precio observado.</p>
          {data.basket.items.length ? (
            <ol>
              {data.basket.items.slice(0, 10).map((item) => (
                <li key={item.product_id}>
                  <button onClick={() => onShowProduct(item.product_id)}>
                    <strong>{item.name}</strong>
                    <small>
                      {formatQuantity(item.typical_quantity ?? "0")}{" "}
                      {item.price_unit === "€/kg" ? "kg" : "ud"} ×{" "}
                      {formatMoney(item.current_price ?? "0")} ={" "}
                      {formatMoney(
                        String(
                          Number(item.typical_quantity ?? 0) *
                            Number(item.current_price ?? 0),
                        ),
                      )}
                    </small>
                  </button>
                </li>
              ))}
            </ol>
          ) : (
            <p className="empty">
              Aún no hay productos con un patrón suficientemente estable.
            </p>
          )}
        </section>
        <LineChart
          title="Evolución de tu cesta habitual"
          subtitle="La cobertura indica cuántos productos tenían un precio conocido"
          points={data.basket.basket_price_history.map((point) => ({
            label: formatMonth(point.month),
            value: Number(point.cost),
          }))}
        />
      </section>
      {inflation && (
        <section className="card inflation-card">
          <p className="eyebrow">Inflación de tu cesta</p>
          <h2>
            {Number(inflation.change_percent) > 0
              ? "↑"
              : Number(inflation.change_percent) < 0
                ? "↓"
                : "="}{" "}
            {Number(inflation.change_percent).toLocaleString("es-ES", {
              maximumFractionDigits: 1,
            })}{" "}
            %
          </h2>
          <p>
            Comparado con {formatMonth(inflation.baseline_month)}:{" "}
            {formatMoney(inflation.baseline_cost)} →{" "}
            {formatMoney(inflation.current_cost)}. Cobertura inicial:{" "}
            {Number(inflation.coverage_baseline) * 100} %.
          </p>
        </section>
      )}
      <section className="insight-grid habits-grid">
        <HabitList
          title="Puede que toque comprar"
          items={data.due_soon_products}
          detail={(item) =>
            `${item.status === "retrasado" ? "Retrasado" : item.status === "toca" ? "Toca" : "Pronto"} · hace ${item.days_since_last_purchase} días · sueles comprarlo cada ${item.median_days_between_purchases} días`
          }
          onSelect={onShowProduct}
        />
        <HabitList
          title="Más recurrentes"
          items={data.most_regular_products}
          detail={(item) =>
            `${item.purchase_count} compras · cada ${item.median_days_between_purchases} días`
          }
          onSelect={onShowProduct}
        />
        <HabitList
          title="Nuevos en tus compras"
          items={data.new_products}
          detail={(item) =>
            `Primera compra: ${formatDate(item.first_purchased_at)}`
          }
          onSelect={onShowProduct}
        />
        <HabitList
          title="Ya no aparecen tanto"
          items={data.inactive_regular_products}
          detail={(item) =>
            `Última compra hace ${item.days_since_last_purchase} días · antes cada ${item.median_days_between_purchases} días`
          }
          onSelect={onShowProduct}
        />
      </section>
    </>
  );
}

export function HabitList({
  title,
  items,
  detail,
  onSelect,
}: {
  title: string;
  items: HabitProduct[];
  detail: (item: HabitProduct) => string;
  onSelect: (id: number) => void;
}) {
  return (
    <section className="card insight-ranking">
      <h3>{title}</h3>
      {items.length ? (
        <ol>
          {items.map((item) => (
            <li key={item.product_id}>
              <button onClick={() => onSelect(item.product_id)}>
                <strong>{item.name}</strong>
                <small>{detail(item)}</small>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="empty">No hay datos suficientes.</p>
      )}
    </section>
  );
}

export function Statistics({
  section,
  error,
  pricesError,
  categoriesError,
  data,
  insights,
  categoryData,
  range,
  onRangeChange,
  topProducts,
  onShowProduct,
}: {
  error: boolean;
  pricesError: boolean;
  categoriesError: boolean;
  section: "gastos" | "categorias" | "precios";
  data: Statistics | null;
  insights: ProductInsights | null;
  categoryData: CategoryAnalytics | null;
  range: StatisticsRange;
  onRangeChange: (range: StatisticsRange) => void;
  topProducts: ProductSummary[];
  onShowProduct: (id: number) => void;
}) {
  const dayLabels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
  const peakHour = data?.purchases_by_hour.reduce<{
    hour: number;
    receipt_count: number;
  } | null>(
    (best, item) =>
      !best || item.receipt_count > best.receipt_count ? item : best,
    null,
  );
  return (
    <>
      <header className="statistics-heading">
        <div>
          <p className="eyebrow">
            {section === "precios" ? "Todo el histórico" : "Periodo"}
          </p>
          <h2>
            {section === "gastos"
              ? "Evolución del gasto"
              : section === "categorias"
                ? "Gasto por categorías"
                : "Productos y precios"}
          </h2>
        </div>
        {section !== "precios" && (
          <div className="range-selector" aria-label="Periodo de estadísticas">
            {(
              [
                ["3m", "3 meses"],
                ["6m", "6 meses"],
                ["1y", "1 año"],
                ["all", "Todo"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                className={range === value ? "active" : ""}
                aria-pressed={range === value}
                onClick={() => onRangeChange(value)}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </header>
      {section === "gastos" &&
        (!data ? (
          <p role="status">
            {error
              ? "No se han podido cargar las estadísticas. Vuelve a entrar en Análisis para reintentar."
              : "Cargando estadísticas…"}
          </p>
        ) : (
          <>
            <section
              className="statistics-metrics"
              aria-label="Métricas del periodo"
            >
              <Metric
                label="Gasto"
                value={formatMoney(data.period.total_spend)}
              />
              <Metric
                label="Compras"
                value={String(data.period.receipt_count)}
              />
              <Metric
                label="Ticket medio"
                value={formatMoney(data.period.average_basket)}
              />
              <Metric
                label="Media semanal"
                value={formatMoney(data.period.average_weekly_spend)}
              />
              <Metric
                label="Intervalo medio"
                value={
                  data.period.average_days_between_shops
                    ? `Cada ${data.period.average_days_between_shops.replace(".", ",")} días`
                    : "Sin datos suficientes"
                }
              />
            </section>
            <section className="comparison-grid">
              <ComparisonCard
                title="Este mes"
                comparison={data.comparisons.current_month}
              />
              <ComparisonCard
                title="Este año"
                comparison={data.comparisons.current_year}
              />
            </section>
            <section className="chart-grid statistics-charts">
              <LineChart
                title="Evolución del gasto"
                subtitle="Gasto total por mes"
                points={data.monthly_spend.map((point) => ({
                  label: formatMonth(point.month),
                  value: Number(point.total_spend),
                }))}
              />
              <BarChart
                title="Compras por mes"
                subtitle="Tickets realizados cada mes"
                points={data.monthly_spend.map((point) => ({
                  label: formatMonth(point.month),
                  value: point.receipt_count,
                }))}
              />
              <BarChart
                title="Compras por día de la semana"
                subtitle="Día habitual de compra"
                points={data.purchases_by_weekday.map((point, index) => ({
                  label: dayLabels[index],
                  value: point.receipt_count,
                }))}
              />
              <BarChart
                title="Compras por hora"
                subtitle={
                  peakHour?.receipt_count
                    ? `Hora más habitual: ${String(peakHour.hour).padStart(2, "0")}:00`
                    : "Aún no hay horas de compra registradas"
                }
                points={data.purchases_by_hour.map((point) => ({
                  label: `${String(point.hour).padStart(2, "0")}:00`,
                  value: point.receipt_count,
                }))}
              />
            </section>
          </>
        ))}
      {section === "precios" && (
        <>
          <section className="insights-section">
            <p className="eyebrow">Productos y precios</p>
            <h2>Qué productos marcan tu compra.</h2>
            {insights ? (
              <div className="insight-grid">
                <InsightRanking
                  title="Productos en los que más gastas"
                  items={insights.most_expensive_by_spend}
                  kind="spend"
                  onSelect={onShowProduct}
                />
                <InsightRanking
                  title="Más comprados"
                  items={insights.most_frequently_purchased}
                  kind="frequency"
                  onSelect={onShowProduct}
                />
                <InsightRanking
                  title="Mayores subidas"
                  items={insights.biggest_price_increases_percent}
                  kind="change"
                  onSelect={onShowProduct}
                />
                <InsightRanking
                  title="Mayores bajadas"
                  items={insights.biggest_price_decreases_percent}
                  kind="change"
                  onSelect={onShowProduct}
                />
              </div>
            ) : (
              <p role="status">
                {pricesError
                  ? "No se han podido cargar los precios. Vuelve a entrar en Análisis para reintentar."
                  : "Cargando análisis de productos…"}
              </p>
            )}
          </section>
          <TopProducts
            title="Top de productos"
            products={topProducts}
            onSelect={onShowProduct}
          />
        </>
      )}
      {section === "categorias" && (
        <CategoryDashboard
          data={categoryData}
          error={categoriesError}
          onShowProduct={onShowProduct}
        />
      )}
    </>
  );
}

export function CategoryDashboard({
  data,
  error,
  onShowProduct,
}: {
  data: CategoryAnalytics | null;
  error: boolean;
  onShowProduct: (id: number) => void;
}) {
  const [selectedSlug, setSelectedSlug] = useState("");
  useEffect(() => {
    if (!selectedSlug && data?.categories[0])
      setSelectedSlug(data.categories[0].slug);
  }, [data, selectedSlug]);
  if (!data)
    return (
      <section className="insights-section">
        <p className="eyebrow">Categorías</p>
        <p role="status">
          {error
            ? "No se han podido cargar las categorías. Vuelve a entrar en Análisis para reintentar."
            : "Cargando categorías…"}
        </p>
      </section>
    );
  const selected =
    data.categories.find((category) => category.slug === selectedSlug) ??
    data.categories[0];
  const points = data.monthly_spend.map((month) => ({
    label: formatMonth(month.month),
    value: Number(
      month.categories.find((category) => category.slug === selected?.slug)
        ?.total_spend ?? "0",
    ),
  }));
  return (
    <section className="insights-section">
      <p className="eyebrow">Categorías</p>
      <h2>En qué se va tu compra.</h2>
      <section className="category-metrics">
        <Metric
          label="Mayor categoría"
          value={
            data.categories[0]
              ? `${data.categories[0].name} · ${formatMoney(data.categories[0].total_spend)}`
              : "Sin datos"
          }
        />
        <Metric
          label="Clasificados"
          value={`${data.summary.categorized_products} / ${data.summary.total_products}`}
        />
        <Metric
          label="Sin categoría"
          value={String(data.summary.uncategorized_products)}
        />
      </section>
      <section className="chart-grid">
        <BarChart
          title="Gasto por categoría"
          subtitle={`Gasto observado: ${formatMoney(data.summary.observed_spend)}`}
          points={data.categories
            .filter((category) => Number(category.total_spend) > 0)
            .map((category) => ({
              label: category.name,
              value: Number(category.total_spend),
              detail: `${formatMoney(category.total_spend)} · ${Number(category.percentage).toLocaleString("es-ES", { maximumFractionDigits: 1 })} %`,
            }))}
        />
        <section className="card category-detail">
          <label>
            Ver evolución de
            <select
              value={selected?.slug ?? ""}
              onChange={(event) => setSelectedSlug(event.target.value)}
            >
              {data.categories.map((category) => (
                <option key={category.slug} value={category.slug}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          {selected && (
            <>
              <p>
                <strong>{selected.name}</strong> ·{" "}
                {formatMoney(selected.total_spend)} ·{" "}
                {Number(selected.percentage).toLocaleString("es-ES", {
                  maximumFractionDigits: 1,
                })}{" "}
                %
              </p>
              <LineChart
                title="Evolución por categoría"
                subtitle={selected.name}
                points={points}
              />
              <h3>Cambio respecto al mes anterior</h3>
              <p>
                {Number(selected.change_absolute) > 0
                  ? "↑"
                  : Number(selected.change_absolute) < 0
                    ? "↓"
                    : "="}{" "}
                {selected.change_percent === null
                  ? "Sin periodo anterior comparable"
                  : `${Number(selected.change_percent).toLocaleString("es-ES", { maximumFractionDigits: 1 })} %`}{" "}
                · {formatMoney(selected.change_absolute)}
              </p>
              <h3>Productos con mayor gasto</h3>
              {selected.top_products.length ? (
                <ol className="category-products">
                  {selected.top_products.map((product) => (
                    <li key={product.id}>
                      <button onClick={() => onShowProduct(product.id)}>
                        {product.name}
                        <small>{formatMoney(product.total_spend)}</small>
                      </button>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="empty">No hay productos con gasto observado.</p>
              )}
            </>
          )}
        </section>
      </section>
    </section>
  );
}

export function InsightRanking({
  title,
  items,
  kind,
  onSelect,
}: {
  title: string;
  items: InsightProduct[];
  kind: "spend" | "frequency" | "change";
  onSelect: (id: number) => void;
}) {
  return (
    <section className="card insight-ranking">
      <h3>{title}</h3>
      {items.length ? (
        <ol>
          {items.map((item, index) => {
            const change = Number(item.change_percent ?? 0);
            const signal = change > 0 ? "↑" : change < 0 ? "↓" : "=";
            return (
              <li key={`${item.id}-${item.price_unit ?? ""}`}>
                <button onClick={() => onSelect(item.id)}>
                  <span>
                    <b>{index + 1}</b>
                    <strong>{item.name}</strong>
                  </span>
                  {kind === "spend" && (
                    <small>
                      {formatMoney(item.total_spend ?? "0")} ·{" "}
                      {item.purchase_count} compras
                    </small>
                  )}
                  {kind === "frequency" && (
                    <small>
                      {item.purchase_count} compras · última{" "}
                      {formatDate(item.last_purchased_at)}
                    </small>
                  )}
                  {kind === "change" && (
                    <small
                      aria-label={`${signal} ${change.toLocaleString("es-ES", { maximumFractionDigits: 1 })} por ciento`}
                    >
                      {formatMoney(item.previous_price ?? "0")} →{" "}
                      {formatMoney(item.current_price ?? "0")} · {signal}{" "}
                      {change.toLocaleString("es-ES", {
                        maximumFractionDigits: 1,
                      })}{" "}
                      % ({item.price_unit})
                    </small>
                  )}
                </button>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="empty">Aún no hay histórico suficiente.</p>
      )}
    </section>
  );
}

export function ComparisonCard({
  title,
  comparison,
}: {
  title: string;
  comparison: Comparison;
}) {
  const difference = Number(comparison.difference);
  const signal = difference > 0 ? "↑" : difference < 0 ? "↓" : "=";
  const sign = difference > 0 ? "+" : "";
  const percentage =
    comparison.percentage_change === null
      ? "Sin periodo anterior comparable"
      : `${signal} ${sign}${Number(comparison.percentage_change).toLocaleString("es-ES", { maximumFractionDigits: 1 })} %`;
  return (
    <section className="card comparison-card">
      <p>{title}</p>
      <h2>{formatMoney(comparison.current)}</h2>
      <strong>{percentage}</strong>
      <small>
        {sign}
        {formatMoney(comparison.difference)} respecto al periodo anterior
      </small>
    </section>
  );
}
