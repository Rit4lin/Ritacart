import { ChangeEvent, useEffect, useState } from 'react'

type Page = 'inicio' | 'compras' | 'productos' | 'estadisticas' | 'configuracion'
type ImportStatus = { enabled: boolean; last_run: string | null; last_success: string | null; last_error: string | null; imported_receipts_last_run: number }
type ReceiptSummary = { id: number; store: string; purchased_at: string; total: string; source_filename: string; imported_at: string; item_count: number }
type ReceiptDetail = ReceiptSummary & { items: Array<{ id: number; raw_name: string; quantity: string | null; unit: string | null; unit_price: string | null; price_per_kg: string | null; total_price: string | null }>; vat_breakdown: Array<{ rate: string; taxable_base: string; tax_amount: string }> }
type ProductSummary = { id: number; name: string; purchase_count: number; total_quantity: string; last_purchased_at: string | null; category: { id: number; name: string; slug: string } | null }
type Category = { id: number; name: string; slug: string; product_count: number }
type PriceSummary = { price_unit: string; current_price: string; previous_price: string | null; change_absolute: string | null; change_percent: string | null; min_price: string; max_price: string; average_price: string }
type ProductAnalytics = ProductSummary & { aliases: string[]; first_purchased_at: string | null; total_spend: string; average_days_between_purchases: string | null; price_summary: PriceSummary[]; monthly_purchases: Array<{ month: string; purchase_count: number; total_quantity: string }>; monthly_spend: Array<{ month: string; total_spend: string }>; seasonal_purchases: Array<{ month: number; purchase_count: number }>; price_history: Array<{ date: string; price: string; price_unit: string }> }
type Overview = { total_spend: string; receipt_count: number; current_month_spend: string; latest_receipt: ReceiptSummary | null }
type StatisticsRange = '3m' | '6m' | '1y' | 'all'
type Statistics = {
  range: StatisticsRange
  period: { total_spend: string; receipt_count: number; average_basket: string; average_weekly_spend: string; average_days_between_shops: string | null }
  comparisons: { current_month: Comparison; current_year: Comparison }
  monthly_spend: Array<{ month: string; total_spend: string; receipt_count: number; average_basket: string }>
  purchases_by_weekday: Array<{ weekday: number; receipt_count: number }>
  purchases_by_hour: Array<{ hour: number; receipt_count: number }>
}
type Comparison = { current: string; previous: string; difference: string; percentage_change: string | null }
type InsightProduct = { id: number; name: string; purchase_count: number; last_purchased_at: string | null; total_spend?: string; price_unit?: string; current_price?: string; previous_price?: string | null; change_absolute?: string | null; change_percent?: string | null }
type ProductInsights = { most_expensive_by_spend: InsightProduct[]; most_frequently_purchased: InsightProduct[]; biggest_price_increases_percent: InsightProduct[]; biggest_price_decreases_percent: InsightProduct[]; biggest_price_increases_absolute: InsightProduct[]; biggest_price_decreases_absolute: InsightProduct[] }
type CategoryAnalytics = { range: StatisticsRange; summary: { total_products: number; categorized_products: number; uncategorized_products: number; categorized_percentage: string; observed_spend: string }; categories: Array<{ category_id: number | null; name: string; slug: string; total_spend: string; percentage: string; product_count: number; current_month_spend: string; previous_month_spend: string; change_absolute: string; change_percent: string | null; top_products: Array<{ id: number; name: string; total_spend: string }> }>; monthly_spend: Array<{ month: string; categories: Array<{ category_id: number | null; slug: string; total_spend: string }> }> }

const euro = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' })
const dateTime = new Intl.DateTimeFormat('es-ES', { dateStyle: 'medium', timeStyle: 'short' })
const months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
const formatMoney = (value: string) => euro.format(Number(value))
const formatQuantity = (value: string) => new Intl.NumberFormat('es-ES', { maximumFractionDigits: 3 }).format(Number(value))
const formatDate = (value: string | null) => value ? dateTime.format(new Date(value)) : 'Todavía no disponible'
const formatMonth = (value: string) => new Intl.DateTimeFormat('es-ES', { month: 'short', year: '2-digit' }).format(new Date(`${value}-01T12:00:00`))

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) throw new Error('No se ha podido cargar la información.')
  return response.json() as Promise<T>
}

export default function App() {
  const [page, setPage] = useState<Page>('inicio')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [receipts, setReceipts] = useState<ReceiptSummary[]>([])
  const [selectedReceipt, setSelectedReceipt] = useState<ReceiptDetail | null>(null)
  const [products, setProducts] = useState<ProductSummary[]>([])
  const [selectedProduct, setSelectedProduct] = useState<ProductAnalytics | null>(null)
  const [topProducts, setTopProducts] = useState<ProductSummary[]>([])
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null)
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [statisticsRange, setStatisticsRange] = useState<StatisticsRange>('6m')
  const [productInsights, setProductInsights] = useState<ProductInsights | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [categoryAnalytics, setCategoryAnalytics] = useState<CategoryAnalytics | null>(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    setLoading(true)
    try {
      const [nextOverview, nextStatus] = await Promise.all([getJson<Overview>('/api/overview'), getJson<ImportStatus>('/api/import/status')])
      setOverview(nextOverview)
      setImportStatus(nextStatus)
    } catch { setMessage('No se ha podido contactar con RitaCart.') } finally { setLoading(false) }
  }
  const loadReceipts = async () => {
    try { setReceipts(await getJson<ReceiptSummary[]>('/api/receipts')) } catch { setMessage('No se han podido cargar los tickets.') }
  }
  const loadProducts = async () => {
    try { setProducts(await getJson<ProductSummary[]>('/api/products')) } catch { setMessage('No se han podido cargar los productos.') }
  }
  const loadTopProducts = async () => {
    try { setTopProducts(await getJson<ProductSummary[]>('/api/analytics/products/top')) } catch { setMessage('No se ha podido cargar el ranking de productos.') }
  }
  const loadCategories = async () => {
    try { setCategories(await getJson<Category[]>('/api/categories')) } catch { setMessage('No se han podido cargar las categorías.') }
  }
  const loadStatistics = async (range: StatisticsRange) => {
    try { setStatistics(await getJson<Statistics>(`/api/analytics/statistics?range=${range}`)) } catch { setMessage('No se han podido cargar las estadísticas.') }
  }
  const loadProductInsights = async () => {
    try { setProductInsights(await getJson<ProductInsights>('/api/analytics/products/insights')) } catch { setMessage('No se han podido cargar los análisis de productos.') }
  }
  const loadCategoryAnalytics = async (range: StatisticsRange) => {
    try { setCategoryAnalytics(await getJson<CategoryAnalytics>(`/api/analytics/categories?range=${range}`)) } catch { setMessage('No se han podido cargar las estadísticas de categorías.') }
  }
  useEffect(() => { void Promise.all([refresh(), loadReceipts(), loadProducts(), loadTopProducts(), loadCategories()]) }, [])
  useEffect(() => { if (page === 'estadisticas') void Promise.all([loadStatistics(statisticsRange), loadProductInsights(), loadCategoryAnalytics(statisticsRange)]) }, [page, statisticsRange])

  const showReceipt = async (id: number) => {
    try { setSelectedReceipt(await getJson<ReceiptDetail>(`/api/receipts/${id}`)); setPage('compras') } catch { setMessage('No se ha podido abrir el ticket.') }
  }
  const showProduct = async (id: number) => {
    try { setSelectedProduct(await getJson<ProductAnalytics>(`/api/products/${id}/analytics`)); setPage('productos') } catch { setMessage('No se ha podido abrir el producto.') }
  }
  const uploadPdf = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    setMessage('Importando PDF…')
    try {
      const response = await fetch('/api/receipts/import', { method: 'POST', body: formData })
      const result = await response.json() as { receipt_id?: number; duplicate?: boolean; detail?: string }
      if (!response.ok) throw new Error(result.detail ?? 'No se ha podido importar el PDF.')
      await Promise.all([refresh(), loadReceipts(), loadProducts(), loadTopProducts()])
      setMessage(result.duplicate ? 'Este PDF ya estaba importado.' : 'Ticket importado correctamente.')
      if (result.receipt_id) await showReceipt(result.receipt_id)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'No se ha podido importar el PDF.') } finally { event.target.value = '' }
  }
  const runImport = async () => {
    setMessage('Buscando tickets nuevos…')
    try {
      const response = await fetch('/api/import/run', { method: 'POST' })
      const result = await response.json() as ImportStatus | { detail?: string }
      if (!response.ok) throw new Error('detail' in result ? result.detail : 'La búsqueda ha fallado.')
      setImportStatus(result as ImportStatus)
      await Promise.all([refresh(), loadReceipts(), loadProducts(), loadTopProducts()])
      setMessage('Búsqueda terminada.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'La búsqueda ha fallado.') }
  }
  const reprocessReceipt = async (id: number) => {
    setMessage('Reprocesando ticket…')
    try {
      const response = await fetch(`/api/receipts/${id}/reprocess`, { method: 'POST' })
      const result = await response.json() as { detail?: string }
      if (!response.ok) throw new Error(result.detail ?? 'No se ha podido reprocesar el ticket.')
      await Promise.all([refresh(), loadReceipts(), loadProducts(), loadTopProducts(), showReceipt(id)])
      setMessage('Ticket reprocesado correctamente.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'No se ha podido reprocesar el ticket.') }
  }
  const mergeProduct = async (sourceId: number, targetId: number) => {
    setMessage('Uniendo productos…')
    try {
      const response = await fetch(`/api/products/${sourceId}/merge`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_product_id: targetId }) })
      const result = await response.json() as { product_id?: number; target_name?: string; detail?: string }
      if (!response.ok || !result.product_id) throw new Error(result.detail ?? 'No se han podido unir los productos.')
      await Promise.all([loadProducts(), loadTopProducts(), showProduct(result.product_id)])
      setMessage(`Producto unido a ${result.target_name}.`)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'No se han podido unir los productos.') }
  }
  const renameProduct = async (id: number, name: string) => {
    setMessage('Guardando nombre…')
    try {
      const response = await fetch(`/api/products/${id}/rename`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
      const result = await response.json() as { product_id?: number; name?: string; detail?: string }
      if (!response.ok || !result.product_id) throw new Error(result.detail ?? 'No se ha podido renombrar el producto.')
      await Promise.all([loadProducts(), loadTopProducts(), showProduct(result.product_id)])
      setMessage(`Producto renombrado a ${result.name}.`)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'No se ha podido renombrar el producto.') }
  }
  const setProductCategory = async (id: number, categoryId: number | null) => {
    try {
      const response = await fetch(`/api/products/${id}/category`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category_id: categoryId }) })
      const result = await response.json() as { category?: ProductSummary['category']; detail?: string }
      if (!response.ok) throw new Error(result.detail ?? 'No se ha podido guardar la categoría.')
      setSelectedProduct((current) => current?.id === id ? { ...current, category: result.category ?? null } : current)
      await Promise.all([loadProducts(), loadCategories(), loadCategoryAnalytics(statisticsRange)])
      setMessage('Categoría actualizada.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'No se ha podido guardar la categoría.') }
  }

  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><span>R</span><strong>RitaCart</strong></div><nav aria-label="Navegación principal">{([['inicio', 'Inicio'], ['compras', 'Compras'], ['productos', 'Productos'], ['estadisticas', 'Estadísticas'], ['configuracion', 'Configuración']] as const).map(([id, label]) => <button className={page === id ? 'nav-item active' : 'nav-item'} key={id} onClick={() => setPage(id)}>{label}</button>)}</nav><p className="sidebar-note">Datos guardados localmente en tu instalación.</p></aside>
    <main className="content">{message && <p className="notice" role="status">{message}</p>}{page === 'inicio' && <Home overview={overview} topProducts={topProducts} loading={loading} onShowReceipt={showReceipt} onShowProduct={showProduct} />}{page === 'compras' && <Purchases receipts={receipts} selected={selectedReceipt} onSelect={showReceipt} onUpload={uploadPdf} onReprocess={reprocessReceipt} />}{page === 'productos' && <Products products={products} categories={categories} selected={selectedProduct} onSelect={showProduct} onMerge={mergeProduct} onRename={renameProduct} onCategoryChange={setProductCategory} />}{page === 'estadisticas' && <Statistics data={statistics} insights={productInsights} categoryData={categoryAnalytics} range={statisticsRange} onRangeChange={setStatisticsRange} topProducts={topProducts} onShowProduct={showProduct} />}{page === 'configuracion' && <Configuration status={importStatus} onRun={runImport} />}</main>
  </div>
}

function Home({ overview, topProducts, loading, onShowReceipt, onShowProduct }: { overview: Overview | null; topProducts: ProductSummary[]; loading: boolean; onShowReceipt: (id: number) => void; onShowProduct: (id: number) => void }) {
  return <><header><p className="eyebrow">Resumen</p><h1>La compra, de un vistazo.</h1></header>{loading || !overview ? <p>Cargando datos…</p> : <><section className="metrics" aria-label="Resumen de gastos"><Metric label="Gasto total" value={formatMoney(overview.total_spend)} /><Metric label="Compras" value={String(overview.receipt_count)} /><Metric label="Este mes" value={formatMoney(overview.current_month_spend)} /></section><section className="card latest"><div><p className="eyebrow">Última compra</p>{overview.latest_receipt ? <><h2>{formatMoney(overview.latest_receipt.total)}</h2><p>{formatDate(overview.latest_receipt.purchased_at)} · {overview.latest_receipt.item_count} productos</p></> : <p>Aún no hay tickets importados.</p>}</div>{overview.latest_receipt && <button onClick={() => onShowReceipt(overview.latest_receipt!.id)}>Ver ticket</button>}</section>{topProducts.length > 0 && <TopProducts title="Productos más comprados" products={topProducts} onSelect={onShowProduct} />}</>}</>
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

function Products({ products, categories, selected, onSelect, onMerge, onRename, onCategoryChange }: { products: ProductSummary[]; categories: Category[]; selected: ProductAnalytics | null; onSelect: (id: number) => void; onMerge: (sourceId: number, targetId: number) => void; onRename: (id: number, name: string) => void; onCategoryChange: (id: number, categoryId: number | null) => void }) {
  const [uncategorizedOnly, setUncategorizedOnly] = useState(false)
  const visibleProducts = uncategorizedOnly ? products.filter((product) => !product.category) : products
  return <><header><p className="eyebrow">Catálogo</p><h1>Productos</h1></header><div className="product-layout"><section className="card product-list"><label className="product-filter"><input type="checkbox" checked={uncategorizedOnly} onChange={(event) => setUncategorizedOnly(event.target.checked)} /> Solo sin categoría</label>{visibleProducts.length ? visibleProducts.map((product) => <button className={selected?.id === product.id ? 'product-row selected' : 'product-row'} key={product.id} onClick={() => onSelect(product.id)}><strong>{product.name}</strong><small>{product.category?.name ?? 'Sin categoría'} · {product.purchase_count} compras · cantidad {formatQuantity(product.total_quantity)}</small></button>) : <p className="empty">No hay productos que mostrar.</p>}</section><ProductDetail product={selected} products={products} categories={categories} onMerge={onMerge} onRename={onRename} onCategoryChange={onCategoryChange} /></div></>
}

function ProductDetail({ product, products, categories, onMerge, onRename, onCategoryChange }: { product: ProductAnalytics | null; products: ProductSummary[]; categories: Category[]; onMerge: (sourceId: number, targetId: number) => void; onRename: (id: number, name: string) => void; onCategoryChange: (id: number, categoryId: number | null) => void }) {
  if (!product) return <section className="card detail empty">Selecciona un producto para consultar su historial.</section>
  return <ProductDashboard product={product} products={products} categories={categories} onMerge={onMerge} onRename={onRename} onCategoryChange={onCategoryChange} />
}

function ProductDashboard({ product, products, categories, onMerge, onRename, onCategoryChange }: { product: ProductAnalytics; products: ProductSummary[]; categories: Category[]; onMerge: (sourceId: number, targetId: number) => void; onRename: (id: number, name: string) => void; onCategoryChange: (id: number, categoryId: number | null) => void }) {
  const [name, setName] = useState(product.name)
  useEffect(() => setName(product.name), [product.id, product.name])
  const priceSeries = new Map<string, ProductAnalytics['price_history']>()
  product.price_history.forEach((point) => priceSeries.set(point.price_unit, [...(priceSeries.get(point.price_unit) ?? []), point]))
  return <section className="product-detail"><section className="card"><div className="detail-title"><div><p className="eyebrow">Producto</p><h2>{product.name}</h2><p>{product.purchase_count} compras · cantidad acumulada {formatQuantity(product.total_quantity)}</p></div></div><label className="category-control">Categoría<select value={product.category?.id ?? ''} onChange={(event) => onCategoryChange(product.id, event.target.value ? Number(event.target.value) : null)}><option value="">Sin categoría</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label><section className="product-metrics" aria-label="Resumen del producto"><Metric label="Gasto total" value={formatMoney(product.total_spend)} /><Metric label="Comprado" value={`${product.purchase_count} veces`} /><Metric label="Frecuencia" value={product.average_days_between_purchases ? `Cada ${product.average_days_between_purchases.replace('.', ',')} días` : 'Sin histórico suficiente'} /><Metric label="Primera compra" value={formatDate(product.first_purchased_at)} /><Metric label="Última compra" value={formatDate(product.last_purchased_at)} /></section>{product.price_summary.length ? <section className="price-summaries">{product.price_summary.map((summary) => <PriceSummaryCard key={summary.price_unit} summary={summary} />)}</section> : <p className="empty">No hay precios observados para este producto.</p>}<form className="rename-control" onSubmit={(event) => { event.preventDefault(); if (name.trim() && name.trim() !== product.name) onRename(product.id, name) }}><label htmlFor="product-name">Nombre mostrado</label><div><input id="product-name" value={name} maxLength={255} onChange={(event) => setName(event.target.value)} /><button type="submit" disabled={!name.trim() || name.trim() === product.name}>Guardar nombre</button></div><small>Los próximos tickets con cualquiera de estos nombres se asociarán a este producto.</small></form><p className="alias-list">Nombres del ticket: {product.aliases.join(' · ')}</p><label className="merge-control">Unir este producto con<select defaultValue="" onChange={(event) => { const targetId = Number(event.target.value); if (targetId) onMerge(product.id, targetId); event.currentTarget.value = '' }}><option value="">Selecciona un producto…</option>{products.filter((candidate) => candidate.id !== product.id).map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.name}</option>)}</select></label></section><section className="chart-grid"><BarChart title="Compras por mes" subtitle="Tickets que contienen el producto" points={product.monthly_purchases.map((point) => ({ label: point.month, value: point.purchase_count, detail: `cantidad ${formatQuantity(point.total_quantity)}` }))} /><BarChart title="Gasto por mes" subtitle="Importe observado en tickets" points={product.monthly_spend.map((point) => ({ label: point.month, value: Number(point.total_spend), detail: formatMoney(point.total_spend) }))} /><BarChart title="Patrón por temporada" subtitle="Compras agrupadas por mes del año" points={product.seasonal_purchases.map((point) => ({ label: months[point.month - 1], value: point.purchase_count }))} />{[...priceSeries.entries()].map(([unit, points]) => <LineChart key={unit} title={`Evolución de precio (${unit})`} subtitle="Máximo observado cada día de compra" points={points.map((point) => ({ label: point.date, value: Number(point.price) }))} />)}</section></section>
}

function PriceSummaryCard({ summary }: { summary: PriceSummary }) {
  const difference = Number(summary.change_absolute ?? 0)
  const signal = difference > 0 ? '↑' : difference < 0 ? '↓' : '='
  const change = summary.change_percent === null ? 'Sin histórico suficiente' : `${signal} ${Number(summary.change_percent).toLocaleString('es-ES', { maximumFractionDigits: 1 })} %`
  return <article className="price-summary"><h3>{summary.price_unit}</h3><dl><dt>Actual</dt><dd>{formatMoney(summary.current_price)}</dd><dt>Anterior</dt><dd>{summary.previous_price ? formatMoney(summary.previous_price) : 'Sin histórico suficiente'}</dd><dt>Variación</dt><dd aria-label={`Variación ${change}`}>{change}</dd><dt>Mínimo</dt><dd>{formatMoney(summary.min_price)}</dd><dt>Máximo</dt><dd>{formatMoney(summary.max_price)}</dd><dt>Media</dt><dd>{formatMoney(summary.average_price)}</dd></dl></article>
}

function Statistics({ data, insights, categoryData, range, onRangeChange, topProducts, onShowProduct }: { data: Statistics | null; insights: ProductInsights | null; categoryData: CategoryAnalytics | null; range: StatisticsRange; onRangeChange: (range: StatisticsRange) => void; topProducts: ProductSummary[]; onShowProduct: (id: number) => void }) {
  const dayLabels = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
  const peakHour = data?.purchases_by_hour.reduce<{ hour: number; receipt_count: number } | null>((best, item) => !best || item.receipt_count > best.receipt_count ? item : best, null)
  return <><header className="statistics-heading"><div><p className="eyebrow">Estadísticas</p><h1>Cómo evoluciona tu compra.</h1></div><div className="range-selector" aria-label="Periodo de estadísticas">{([['3m', '3 meses'], ['6m', '6 meses'], ['1y', '1 año'], ['all', 'Todo']] as const).map(([value, label]) => <button key={value} className={range === value ? 'active' : ''} aria-pressed={range === value} onClick={() => onRangeChange(value)}>{label}</button>)}</div></header>{!data ? <p>Cargando estadísticas…</p> : <><section className="statistics-metrics" aria-label="Métricas del periodo"><Metric label="Gasto" value={formatMoney(data.period.total_spend)} /><Metric label="Compras" value={String(data.period.receipt_count)} /><Metric label="Ticket medio" value={formatMoney(data.period.average_basket)} /><Metric label="Media semanal" value={formatMoney(data.period.average_weekly_spend)} /><Metric label="Intervalo medio" value={data.period.average_days_between_shops ? `Cada ${data.period.average_days_between_shops.replace('.', ',')} días` : 'Sin datos suficientes'} /></section><section className="comparison-grid"><ComparisonCard title="Este mes" comparison={data.comparisons.current_month} /><ComparisonCard title="Este año" comparison={data.comparisons.current_year} /></section><section className="chart-grid statistics-charts"><LineChart title="Evolución del gasto" subtitle="Gasto total por mes" points={data.monthly_spend.map((point) => ({ label: formatMonth(point.month), value: Number(point.total_spend) }))} /><BarChart title="Compras por mes" subtitle="Tickets realizados cada mes" points={data.monthly_spend.map((point) => ({ label: formatMonth(point.month), value: point.receipt_count }))} /><BarChart title="Compras por día de la semana" subtitle="Día habitual de compra" points={data.purchases_by_weekday.map((point, index) => ({ label: dayLabels[index], value: point.receipt_count }))} /><BarChart title="Compras por hora" subtitle={peakHour?.receipt_count ? `Hora más habitual: ${String(peakHour.hour).padStart(2, '0')}:00` : 'Aún no hay horas de compra registradas'} points={data.purchases_by_hour.map((point) => ({ label: `${String(point.hour).padStart(2, '0')}:00`, value: point.receipt_count }))} /></section></>}<section className="insights-section"><p className="eyebrow">Productos y precios</p><h2>Qué productos marcan tu compra.</h2>{insights ? <div className="insight-grid"><InsightRanking title="Productos en los que más gastas" items={insights.most_expensive_by_spend} kind="spend" onSelect={onShowProduct} /><InsightRanking title="Más comprados" items={insights.most_frequently_purchased} kind="frequency" onSelect={onShowProduct} /><InsightRanking title="Mayores subidas" items={insights.biggest_price_increases_percent} kind="change" onSelect={onShowProduct} /><InsightRanking title="Mayores bajadas" items={insights.biggest_price_decreases_percent} kind="change" onSelect={onShowProduct} /></div> : <p>Cargando análisis de productos…</p>}</section><CategoryDashboard data={categoryData} onShowProduct={onShowProduct} /><TopProducts title="Top de productos" products={topProducts} onSelect={onShowProduct} /></>
}

function CategoryDashboard({ data, onShowProduct }: { data: CategoryAnalytics | null; onShowProduct: (id: number) => void }) {
  const [selectedSlug, setSelectedSlug] = useState('')
  useEffect(() => { if (!selectedSlug && data?.categories[0]) setSelectedSlug(data.categories[0].slug) }, [data, selectedSlug])
  if (!data) return <section className="insights-section"><p className="eyebrow">Categorías</p><p>Cargando categorías…</p></section>
  const selected = data.categories.find((category) => category.slug === selectedSlug) ?? data.categories[0]
  const points = data.monthly_spend.map((month) => ({ label: formatMonth(month.month), value: Number(month.categories.find((category) => category.slug === selected?.slug)?.total_spend ?? '0') }))
  return <section className="insights-section"><p className="eyebrow">Categorías</p><h2>En qué se va tu compra.</h2><section className="category-metrics"><Metric label="Mayor categoría" value={data.categories[0] ? `${data.categories[0].name} · ${formatMoney(data.categories[0].total_spend)}` : 'Sin datos'} /><Metric label="Clasificados" value={`${data.summary.categorized_products} / ${data.summary.total_products}`} /><Metric label="Sin categoría" value={String(data.summary.uncategorized_products)} /></section><section className="chart-grid"><BarChart title="Gasto por categoría" subtitle={`Gasto observado: ${formatMoney(data.summary.observed_spend)}`} points={data.categories.filter((category) => Number(category.total_spend) > 0).map((category) => ({ label: category.name, value: Number(category.total_spend), detail: `${formatMoney(category.total_spend)} · ${Number(category.percentage).toLocaleString('es-ES', { maximumFractionDigits: 1 })} %` }))} /><section className="card category-detail"><label>Ver evolución de<select value={selected?.slug ?? ''} onChange={(event) => setSelectedSlug(event.target.value)}>{data.categories.map((category) => <option key={category.slug} value={category.slug}>{category.name}</option>)}</select></label>{selected && <><p><strong>{selected.name}</strong> · {formatMoney(selected.total_spend)} · {selected.percentage} %</p><LineChart title="Evolución por categoría" subtitle={selected.name} points={points} /><h3>Cambio respecto al mes anterior</h3><p>{Number(selected.change_absolute) > 0 ? '↑' : Number(selected.change_absolute) < 0 ? '↓' : '='} {selected.change_percent === null ? 'Sin periodo anterior comparable' : `${selected.change_percent} %`} · {formatMoney(selected.change_absolute)}</p><h3>Productos con mayor gasto</h3>{selected.top_products.length ? <ol className="category-products">{selected.top_products.map((product) => <li key={product.id}><button onClick={() => onShowProduct(product.id)}>{product.name}<small>{formatMoney(product.total_spend)}</small></button></li>)}</ol> : <p className="empty">No hay productos con gasto observado.</p>}</>}</section></section></section>
}

function InsightRanking({ title, items, kind, onSelect }: { title: string; items: InsightProduct[]; kind: 'spend' | 'frequency' | 'change'; onSelect: (id: number) => void }) {
  return <section className="card insight-ranking"><h3>{title}</h3>{items.length ? <ol>{items.map((item, index) => { const change = Number(item.change_percent ?? 0); const signal = change > 0 ? '↑' : change < 0 ? '↓' : '='; return <li key={`${item.id}-${item.price_unit ?? ''}`}><button onClick={() => onSelect(item.id)}><span><b>{index + 1}</b><strong>{item.name}</strong></span>{kind === 'spend' && <small>{formatMoney(item.total_spend ?? '0')} · {item.purchase_count} compras</small>}{kind === 'frequency' && <small>{item.purchase_count} compras · última {formatDate(item.last_purchased_at)}</small>}{kind === 'change' && <small aria-label={`${signal} ${change.toLocaleString('es-ES', { maximumFractionDigits: 1 })} por ciento`}>{formatMoney(item.previous_price ?? '0')} → {formatMoney(item.current_price ?? '0')} · {signal} {change.toLocaleString('es-ES', { maximumFractionDigits: 1 })} % ({item.price_unit})</small>}</button></li> })}</ol> : <p className="empty">Aún no hay histórico suficiente.</p>}</section>
}

function ComparisonCard({ title, comparison }: { title: string; comparison: Comparison }) {
  const difference = Number(comparison.difference)
  const signal = difference > 0 ? '↑' : difference < 0 ? '↓' : '='
  const sign = difference > 0 ? '+' : ''
  const percentage = comparison.percentage_change === null ? 'Sin periodo anterior comparable' : `${signal} ${sign}${Number(comparison.percentage_change).toLocaleString('es-ES', { maximumFractionDigits: 1 })} %`
  return <section className="card comparison-card"><p>{title}</p><h2>{formatMoney(comparison.current)}</h2><strong>{percentage}</strong><small>{sign}{formatMoney(comparison.difference)} respecto al periodo anterior</small></section>
}

function TopProducts({ title, products, onSelect }: { title: string; products: ProductSummary[]; onSelect: (id: number) => void }) {
  return <section className="card top-products"><h2>{title}</h2>{products.length ? <ol>{products.map((product, index) => <li key={product.id}><button onClick={() => onSelect(product.id)}><span><b>{index + 1}</b><strong>{product.name}</strong></span><small>{product.purchase_count} compras · cantidad {formatQuantity(product.total_quantity)}</small></button></li>)}</ol> : <p className="empty">Aún no hay suficientes datos.</p>}</section>
}

function BarChart({ title, subtitle, points }: { title: string; subtitle: string; points: Array<{ label: string; value: number; detail?: string }> }) {
  const max = Math.max(...points.map((point) => point.value), 1)
  return <section className="card chart"><h2>{title}</h2><p>{subtitle}</p>{points.length ? <div className="bar-chart">{points.map((point) => <div className="bar-row" key={point.label}><span>{point.label}</span><div><i style={{ width: `${(point.value / max) * 100}%` }} /><b>{point.value}</b></div>{point.detail && <small>{point.detail}</small>}</div>)}</div> : <p className="empty">Todavía no hay datos para esta gráfica.</p>}</section>
}

function LineChart({ title, subtitle, points }: { title: string; subtitle: string; points: Array<{ label: string; value: number }> }) {
  if (!points.length) return <section className="card chart"><h2>{title}</h2><p>{subtitle}</p><p className="empty">Todavía no hay datos para esta gráfica.</p></section>
  const width = 600
  const height = 210
  const padding = 28
  const values = points.map((point) => point.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const position = (index: number, value: number) => ({ x: padding + (index * (width - padding * 2)) / Math.max(points.length - 1, 1), y: height - padding - ((value - min) * (height - padding * 2)) / range })
  const path = points.map((point, index) => { const { x, y } = position(index, point.value); return `${index ? 'L' : 'M'} ${x} ${y}` }).join(' ')
  const labelEvery = Math.ceil(points.length / 6)
  return <section className="card chart line-chart"><h2>{title}</h2><p>{subtitle}</p><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}><line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} /><path d={path} />{points.map((point, index) => { const { x, y } = position(index, point.value); const showLabel = index % labelEvery === 0 || index === points.length - 1; return <g key={`${point.label}-${point.value}`}><title>{`${point.label}: ${euro.format(point.value)}`}</title><circle cx={x} cy={y} r="5" />{points.length <= 6 && <text x={x} y={y - 10}>{euro.format(point.value)}</text>}{showLabel && <text x={x} y={height - 8}>{point.label}</text>}</g> })}</svg></section>
}

function Configuration({ status, onRun }: { status: ImportStatus | null; onRun: () => void }) {
  return <><header><p className="eyebrow">Ajustes</p><h1>Configuración</h1></header><section className="card configuration"><div><h2>Importación desde Gmail</h2><p>{status?.enabled ? 'La conexión IMAP está configurada y se revisa periódicamente.' : 'Desactivada: configura EMAIL_USERNAME y EMAIL_PASSWORD para activarla.'}</p></div><span className={status?.enabled ? 'status ready' : 'status'}>{status?.enabled ? 'Activa' : 'Desactivada'}</span><dl><dt>Última revisión</dt><dd>{formatDate(status?.last_run ?? null)}</dd><dt>Última correcta</dt><dd>{formatDate(status?.last_success ?? null)}</dd><dt>Importados en la última revisión</dt><dd>{status?.imported_receipts_last_run ?? 0}</dd><dt>Último error</dt><dd>{status?.last_error ?? 'Ninguno'}</dd></dl><button disabled={!status?.enabled} onClick={onRun}>Buscar nuevos tickets ahora</button></section></>
}
