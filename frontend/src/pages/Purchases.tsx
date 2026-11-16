import { filterReceipts } from "../filters";
import { useState, type ChangeEvent } from "react";
import type { ReceiptSummary, ReceiptDetail } from "../types";
import {
  euro,
  formatMoney,
  formatQuantity,
  formatDate,
  formatPercent,
} from "../format";

export function Purchases({
  receipts,
  state,
  onRetry,
  selected,
  onSelect,
  onUpload,
  onReprocess,
}: {
  receipts: ReceiptSummary[];
  state: "loading" | "ready" | "error";
  onRetry: () => void;
  selected: ReceiptDetail | null;
  onSelect: (id: number) => void;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  onReprocess: (id: number) => void;
}) {
  const [store, setStore] = useState("");
  const [source, setSource] = useState("");
  const [review, setReview] = useState(false);
  const visibleReceipts = filterReceipts(receipts, { store, source, review });
  const stores = [...new Set(receipts.map((receipt) => receipt.store))].sort();
  return (
    <>
      <header className="page-heading">
        <div>
          <p className="eyebrow">Historial</p>
          <h1>Compras</h1>
        </div>
        <div className="upload-group">
          <label className="button upload">
            Importar PDF
            <input
              type="file"
              accept="application/pdf,.pdf"
              aria-label="Seleccionar ticket PDF"
              onChange={onUpload}
            />
          </label>
          <small>
            Para tickets escaneados, aplica OCR en Adobe y guarda el PDF antes
            de subirlo.
          </small>
        </div>
      </header>
      <div className="purchase-layout">
        <section className="card receipt-list">
          <div className="receipt-filters">
            <label>
              Supermercado
              <select
                value={store}
                onChange={(event) => setStore(event.target.value)}
              >
                <option value="">Todos</option>
                {stores.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Origen
              <select
                value={source}
                onChange={(event) => setSource(event.target.value)}
              >
                <option value="">Todos</option>
                <option value="manual">Manual</option>
                <option value="email">Email</option>
              </select>
            </label>
            <label className="check-filter">
              <input
                type="checkbox"
                checked={review}
                onChange={(event) => setReview(event.target.checked)}
              />{" "}
              Solo para revisar
            </label>
            <p>
              {visibleReceipts.length} de {receipts.length} compras
            </p>
          </div>
          {state === "loading" ? (
            <p className="empty" role="status">
              Cargando compras…
            </p>
          ) : state === "error" ? (
            <div className="empty">
              <p>No se han podido cargar las compras.</p>
              <button onClick={onRetry}>Reintentar</button>
            </div>
          ) : visibleReceipts.length ? (
            visibleReceipts.map((receipt) => (
              <button
                className={
                  selected?.id === receipt.id
                    ? "receipt-row selected"
                    : "receipt-row"
                }
                key={receipt.id}
                onClick={() => onSelect(receipt.id)}
              >
                <span>
                  <strong>{formatMoney(receipt.total)}</strong>
                  <small>{formatDate(receipt.purchased_at)}</small>
                </span>
                <small>
                  {receipt.store} ·{" "}
                  {receipt.source === "manual" ? "Manual" : "Email"} ·{" "}
                  {receipt.item_count} productos
                  {receipt.needs_review ? " · Revisar" : ""}
                </small>
              </button>
            ))
          ) : (
            <p className="empty">
              {receipts.length
                ? "No hay compras con estos filtros."
                : "Importa un ticket PDF para empezar."}
            </p>
          )}
        </section>
        <div>
          {selected &&
            state === "ready" &&
            !visibleReceipts.some((receipt) => receipt.id === selected.id) && (
              <p className="notice">
                El ticket abierto no aparece en la lista con los filtros
                actuales.
              </p>
            )}
          <ReceiptDetailPanel receipt={selected} onReprocess={onReprocess} />
        </div>
      </div>
    </>
  );
}

export function ReceiptDetailPanel({
  receipt,
  onReprocess,
}: {
  receipt: ReceiptDetail | null;
  onReprocess: (id: number) => void;
}) {
  if (!receipt)
    return (
      <section className="card detail empty">
        Selecciona un ticket para ver sus productos.
      </section>
    );
  const vatTotal = receipt.vat_breakdown.reduce(
    (total, vat) => total + Number(vat.tax_amount),
    0,
  );
  const lineDiscount = Number(receipt.line_discount_total || "0");
  const hasBreakdown =
    receipt.subtotal !== null ||
    receipt.adjustments.length > 0 ||
    lineDiscount > 0;
  return (
    <section className="card detail">
      <div className="detail-title">
        <div>
          <p className="eyebrow">{receipt.store}</p>
          <h2>{formatMoney(receipt.total)}</h2>
          <p>{formatDate(receipt.purchased_at)}</p>
        </div>
        <div className="detail-actions">
          <span>{receipt.item_count} productos</span>
          <a
            className="receipt-pdf"
            href={"/api/receipts/" + receipt.id + "/pdf"}
            target="_blank"
            rel="noreferrer"
          >
            Abrir ticket original
          </a>
          <button
            onClick={() => {
              if (
                window.confirm(
                  "Se reconstruirán los datos normalizados del ticket desde el PDF original. ¿Continuar?",
                )
              )
                onReprocess(receipt.id);
            }}
          >
            Reprocesar ticket
          </button>
        </div>
      </div>
      {receipt.needs_review && (
        <section className="review-notice">
          <strong>Revisión recomendada</strong>
          {receipt.parser_warnings.length ? (
            <ul>
              {receipt.parser_warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : (
            <p>El ticket no contiene líneas de producto.</p>
          )}
        </section>
      )}
      {hasBreakdown && (
        <section className="vat-summary" aria-label="Desglose de descuentos">
          <strong>Desglose de la compra</strong>
          {lineDiscount > 0 && (
            <small>Descuentos de producto: −{euro.format(lineDiscount)}</small>
          )}
          {receipt.subtotal !== null && (
            <small>
              Subtotal tras ofertas: {formatMoney(receipt.subtotal)}
            </small>
          )}
          {receipt.adjustments.map((adjustment, index) => (
            <small key={index}>
              {adjustment.label}: {formatMoney(adjustment.amount)}
            </small>
          ))}
          <strong>Total pagado: {formatMoney(receipt.total)}</strong>
        </section>
      )}
      {receipt.vat_breakdown.length > 0 && (
        <section className="vat-summary">
          <strong>IVA incluido: {euro.format(vatTotal)}</strong>
          {receipt.vat_breakdown.map((vat) => (
            <small key={vat.rate}>
              {formatPercent(vat.rate)}: base {formatMoney(vat.taxable_base)} ·
              IVA {formatMoney(vat.tax_amount)}
            </small>
          ))}
        </section>
      )}
      <div className="item-table">
        {receipt.items.map((item) => (
          <div className="item-row" key={item.id}>
            <div>
              <strong>{item.raw_name}</strong>
              <small>
                {item.quantity
                  ? formatQuantity(item.quantity) + " " + (item.unit ?? "")
                  : "Cantidad no indicada"}
                {item.price_per_kg
                  ? " · " + formatMoney(item.price_per_kg) + "/kg"
                  : ""}
              </small>
              {Number(item.discount_amount) > 0 && (
                <small>
                  Oferta: −{formatMoney(item.discount_amount)} · Precio
                  original:{" "}
                  {item.gross_total_price
                    ? formatMoney(item.gross_total_price)
                    : "—"}
                </small>
              )}
            </div>
            <strong>
              {item.total_price !== null ? formatMoney(item.total_price) : "—"}
            </strong>
          </div>
        ))}
      </div>
      <details className="technical-data">
        <summary>Datos técnicos: texto extraído</summary>
        <pre>{receipt.source_extracted_text}</pre>
      </details>
    </section>
  );
}
