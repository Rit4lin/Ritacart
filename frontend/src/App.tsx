import { ChangeEvent, useEffect, useState } from 'react'

type Page = 'inicio' | 'compras' | 'configuracion'
type ImportStatus = { enabled: boolean; last_run: string | null; last_success: string | null; last_error: string | null; imported_receipts_last_run: number }
type ReceiptSummary = { id: number; store: string; purchased_at: string; total: string; source_filename: string; imported_at: string; item_count: number }
type ReceiptDetail = ReceiptSummary & { items: Array<{ id: number; raw_name: string; quantity: string | null; unit: string | null; unit_price: string | null; price_per_kg: string | null; total_price: string | null }>; vat_breakdown: Array<{ rate: string; taxable_base: string; tax_amount: string }> }
type Overview = { total_spend: string; receipt_count: number; current_month_spend: string; latest_receipt: ReceiptSummary | null }

const euro = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' })
const dateTime = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })
const formatMoney = (value: string) => euro.format(Number(value))
const formatDate = (value: string | null) => value ? dateTime.format(new Date(value)) : 'Todavía no disponible'

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw new Error('No se ha podido cargar la información.')
  return response.json() as Promise<T>
}

export default function App() {
  const [page, setPage] = useState<Page>('inicio')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [receipts, setReceipts] = useState<ReceiptSummary[]>([])
  const [selected, setSelected] = useState<ReceiptDetail | null>(null)
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    setLoading(true)
    try {
      const [nextOverview, nextStatus] = await Promise.all([getJson<Overview>('/api/overview'), getJson<ImportStatus>('/api/import/status')])
      setOverview(nextOverview); setImportStatus(nextStatus); setMessage('')
    } catch { setMessage('No se ha podido contactar con RitaCart.') } finally { setLoading(false) }
  }
  const loadReceipts = async () => {
    try { setReceipts(await getJson<ReceiptSummary[]>('/api/receipts')) } catch { setMessage('No se han podido cargar los tickets.') }
  }
  useEffect(() => { void refresh(); void loadReceipts() }, [])
  const showReceipt = async (id: number) => {
    try { setSelected(await getJson<ReceiptDetail>(`/api/receipts/${id}`)); setPage('compras') } catch { setMessage('No se ha podido abrir el ticket.') }
  }
  const uploadPdf = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const formData = new FormData(); formData.append('file', file); setMessage('Importando PDF…')
    try {
      const response = await fetch('/api/receipts/import', { method: 'POST', body: formData })
      const result = await response.json() as { receipt_id?: number; duplicate?: boolean; detail?: string }
      if (!response.ok) throw new Error(result.detail ?? 'No se ha podido importar el PDF.')
      setMessage(result.duplicate ? 'Este PDF ya estaba importado.' : 'Ticket importado correctamente.')
      await Promise.all([refresh(), loadReceipts()])
      if (result.receipt_id) await showReceipt(result.receipt_id)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'No se ha podido importar el PDF.') } finally { event.target.value = '' }
  }
  const runImport = async () => {
    setMessage('Buscando tickets nuevos…')
    try {
      const response = await fetch('/api/import/run', { method: 'POST' })
      const result = await response.json() as ImportStatus | { detail?: string }
      if (!response.ok) throw new Error('detail' in result ? result.detail : 'La búsqueda ha fallado.')
      setImportStatus(result as ImportStatus); await Promise.all([refresh(), loadReceipts()]); setMessage('Búsqueda terminada.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'La búsqueda ha fallado.') }
  }
  const reprocessReceipt = async (id: number) => {
    setMessage('Reprocesando ticket…')
    try {
      const response = await fetch(`/api/receipts/${id}/reprocess`, { method: 'POST' })
      const result = await response.json() as { detail?: string }
      if (!response.ok) throw new Error(result.detail ?? 'No se ha podido reprocesar el ticket.')
      await Promise.all([refresh(), loadReceipts(), showReceipt(id)])
      setMessage('Ticket reprocesado correctamente.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'No se ha podido reprocesar el ticket.') }
  }

  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><span>R</span><strong>RitaCart</strong></div><nav aria-label="Navegación principal">{([['inicio', 'Inicio'], ['compras', 'Compras'], ['configuracion', 'Configuración']] as const).map(([id, label]) => <button className={page === id ? 'nav-item active' : 'nav-item'} key={id} onClick={() => setPage(id)}>{label}</button>)}</nav><p className="sidebar-note">Datos guardados localmente en tu instalación.</p></aside>
    <main className="content">{message && <p className="notice" role="status">{message}</p>}{page === 'inicio' && <Home overview={overview} loading={loading} onShowReceipt={showReceipt} />}{page === 'compras' && <Purchases receipts={receipts} selected={selected} onSelect={showReceipt} onUpload={uploadPdf} onReprocess={reprocessReceipt} />}{page === 'configuracion' && <Configuration status={importStatus} onRun={runImport} />}</main>
  </div>
}

function Home({ overview, loading, onShowReceipt }: { overview: Overview | null; loading: boolean; onShowReceipt: (id: number) => void }) {
  return <><header><p className="eyebrow">Resumen</p><h1>La compra, de un vistazo.</h1></header>{loading || !overview ? <p>Cargando datos…</p> : <><section className="metrics" aria-label="Resumen de gastos"><Metric label="Gasto total" value={formatMoney(overview.total_spend)} /><Metric label="Compras" value={String(overview.receipt_count)} /><Metric label="Este mes" value={formatMoney(overview.current_month_spend)} /></section><section className="card latest"><div><p className="eyebrow">Última compra</p>{overview.latest_receipt ? <><h2>{formatMoney(overview.latest_receipt.total)}</h2><p>{formatDate(overview.latest_receipt.purchased_at)} · {overview.latest_receipt.item_count} productos</p></> : <p>Aún no hay tickets importados.</p>}</div>{overview.latest_receipt && <button onClick={() => onShowReceipt(overview.latest_receipt!.id)}>Ver ticket</button>}</section></>}</>
}
function Metric({ label, value }: { label: string; value: string }) { return <article className="metric"><p>{label}</p><strong>{value}</strong></article> }
function Purchases({ receipts, selected, onSelect, onUpload, onReprocess }: { receipts: ReceiptSummary[]; selected: ReceiptDetail | null; onSelect: (id: number) => void; onUpload: (event: ChangeEvent<HTMLInputElement>) => void; onReprocess: (id: number) => void }) {
  return <><header className="page-heading"><div><p className="eyebrow">Historial</p><h1>Compras</h1></div><label className="button upload">Importar PDF<input type="file" accept="application/pdf,.pdf" onChange={onUpload} /></label></header><div className="purchase-layout"><section className="card receipt-list">{receipts.length ? receipts.map((receipt) => <button className={selected?.id === receipt.id ? 'receipt-row selected' : 'receipt-row'} key={receipt.id} onClick={() => onSelect(receipt.id)}><span><strong>{formatMoney(receipt.total)}</strong><small>{formatDate(receipt.purchased_at)}</small></span><small>{receipt.item_count} productos</small></button>) : <p className="empty">Importa un ticket PDF para empezar.</p>}</section><ReceiptDetailPanel receipt={selected} onReprocess={onReprocess} /></div></>
}
function ReceiptDetailPanel({ receipt, onReprocess }: { receipt: ReceiptDetail | null; onReprocess: (id: number) => void }) {
  if (!receipt) return <section className="card detail empty">Selecciona un ticket para ver sus productos.</section>
  const vatTotal = receipt.vat_breakdown.reduce((total, vat) => total + Number(vat.tax_amount), 0)
  return <section className="card detail"><div className="detail-title"><div><p className="eyebrow">{receipt.store}</p><h2>{formatMoney(receipt.total)}</h2><p>{formatDate(receipt.purchased_at)}</p></div><div className="detail-actions"><span>{receipt.item_count} productos</span><button onClick={() => onReprocess(receipt.id)}>Reprocesar ticket</button></div></div>{receipt.vat_breakdown.length > 0 && <section className="vat-summary"><strong>IVA incluido: {euro.format(vatTotal)}</strong>{receipt.vat_breakdown.map((vat) => <small key={vat.rate}>{vat.rate}%: base {formatMoney(vat.taxable_base)} · IVA {formatMoney(vat.tax_amount)}</small>)}</section>}<div className="item-table">{receipt.items.map((item) => <div className="item-row" key={item.id}><div><strong>{item.raw_name}</strong><small>{item.quantity ? `${item.quantity} ${item.unit ?? ''}` : 'Cantidad no indicada'}{item.price_per_kg ? ` · ${formatMoney(item.price_per_kg)}/kg` : ''}</small></div><strong>{item.total_price ? formatMoney(item.total_price) : '—'}</strong></div>)}</div></section>
}
function Configuration({ status, onRun }: { status: ImportStatus | null; onRun: () => void }) {
  return <><header><p className="eyebrow">Ajustes</p><h1>Configuración</h1></header><section className="card configuration"><div><h2>Importación desde Gmail</h2><p>{status?.enabled ? 'La conexión IMAP está configurada y se revisa periódicamente.' : 'Desactivada: configura EMAIL_USERNAME y EMAIL_PASSWORD para activarla.'}</p></div><span className={status?.enabled ? 'status ready' : 'status'}>{status?.enabled ? 'Activa' : 'Desactivada'}</span><dl><dt>Última revisión</dt><dd>{formatDate(status?.last_run ?? null)}</dd><dt>Última correcta</dt><dd>{formatDate(status?.last_success ?? null)}</dd><dt>Importados en la última revisión</dt><dd>{status?.imported_receipts_last_run ?? 0}</dd><dt>Último error</dt><dd>{status?.last_error ?? 'Ninguno'}</dd></dl><button disabled={!status?.enabled} onClick={onRun}>Buscar nuevos tickets ahora</button></section></>
}
