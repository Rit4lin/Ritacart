import { useEffect, useState, type ChangeEvent } from "react";
import type {
  Page,
  ImportStatus,
  ReceiptSummary,
  ReceiptDetail,
  ProductSummary,
  Category,
  ProductAnalytics,
  Overview,
  StatisticsRange,
  Statistics as StatisticsData,
  ProductInsights,
  CategoryAnalytics,
  BasketInsights,
  SearchResults,
  DataHealth,
} from "./types";
import { SearchPanel } from "./components/Common";
import { Home } from "./pages/Home";
import { Purchases } from "./pages/Purchases";
import { Products } from "./pages/Products";
import { Statistics, Habits } from "./pages/Analysis";
import { Configuration } from "./pages/Configuration";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error("No se ha podido cargar la información.");
  return response.json() as Promise<T>;
}

export default function App() {
  const [page, setPage] = useState<Page>("inicio");
  const [analysisSection, setAnalysisSection] = useState<
    "gastos" | "categorias" | "precios" | "habitos"
  >("gastos");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [receipts, setReceipts] = useState<ReceiptSummary[]>([]);
  const [selectedReceipt, setSelectedReceipt] = useState<ReceiptDetail | null>(
    null,
  );
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [selectedProduct, setSelectedProduct] =
    useState<ProductAnalytics | null>(null);
  const [topProducts, setTopProducts] = useState<ProductSummary[]>([]);
  const [importStatus, setImportStatus] = useState<ImportStatus | null>(null);
  const [statistics, setStatistics] = useState<StatisticsData | null>(null);
  const [statisticsRange, setStatisticsRange] = useState<StatisticsRange>("6m");
  const [productInsights, setProductInsights] =
    useState<ProductInsights | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryAnalytics, setCategoryAnalytics] =
    useState<CategoryAnalytics | null>(null);
  const [basketInsights, setBasketInsights] = useState<BasketInsights | null>(
    null,
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResults | null>(
    null,
  );
  const [dataHealth, setDataHealth] = useState<DataHealth | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [analysisError, setAnalysisError] = useState(false);
  const [habitsError, setHabitsError] = useState(false);
  const [pricesError, setPricesError] = useState(false);
  const [categoriesError, setCategoriesError] = useState(false);
  const [receiptsState, setReceiptsState] = useState<
    "loading" | "ready" | "error"
  >("loading");
  const [productsState, setProductsState] = useState<
    "loading" | "ready" | "error"
  >("loading");

  const refresh = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const [nextOverview, nextStatus] = await Promise.all([
        getJson<Overview>("/api/overview"),
        getJson<ImportStatus>("/api/import/status"),
      ]);
      setOverview(nextOverview);
      setImportStatus(nextStatus);
      setMessage((current) =>
        current.startsWith("No se ha podido contactar con RitaCart.")
          ? ""
          : current,
      );
    } catch {
      setLoadError(true);
      setMessage(
        "No se ha podido contactar con RitaCart. Comprueba la conexión e inténtalo de nuevo.",
      );
    } finally {
      setLoading(false);
    }
  };
  const loadReceipts = async () => {
    setReceiptsState("loading");
    try {
      setReceipts(await getJson<ReceiptSummary[]>("/api/receipts"));
      setReceiptsState("ready");
    } catch {
      setReceiptsState("error");
      setMessage("No se han podido cargar los tickets.");
    }
  };
  const loadProducts = async () => {
    setProductsState("loading");
    try {
      setProducts(await getJson<ProductSummary[]>("/api/products"));
      setProductsState("ready");
    } catch {
      setProductsState("error");
      setMessage("No se han podido cargar los productos.");
    }
  };
  const loadTopProducts = async () => {
    try {
      setTopProducts(
        await getJson<ProductSummary[]>("/api/analytics/products/top"),
      );
    } catch {
      setMessage("No se ha podido cargar el ranking de productos.");
    }
  };
  const loadCategories = async () => {
    try {
      setCategories(await getJson<Category[]>("/api/categories"));
    } catch {
      setMessage("No se han podido cargar las categorías.");
    }
  };
  const loadStatistics = async (range: StatisticsRange) => {
    try {
      setAnalysisError(false);
      setStatistics(
        await getJson<StatisticsData>(
          `/api/analytics/statistics?range=${range}`,
        ),
      );
    } catch {
      setAnalysisError(true);
      setMessage("No se han podido cargar las estadísticas.");
    }
  };
  const loadProductInsights = async () => {
    try {
      setPricesError(false);
      setProductInsights(
        await getJson<ProductInsights>("/api/analytics/products/insights"),
      );
    } catch {
      setPricesError(true);
      setMessage("No se han podido cargar los análisis de productos.");
    }
  };
  const loadCategoryAnalytics = async (range: StatisticsRange) => {
    try {
      setCategoriesError(false);
      setCategoryAnalytics(
        await getJson<CategoryAnalytics>(
          `/api/analytics/categories?range=${range}`,
        ),
      );
    } catch {
      setCategoriesError(true);
      setMessage("No se han podido cargar las estadísticas de categorías.");
    }
  };
  const loadBasketInsights = async () => {
    try {
      setHabitsError(false);
      setBasketInsights(await getJson<BasketInsights>("/api/analytics/basket"));
    } catch {
      setHabitsError(true);
      setMessage("No se han podido cargar los hábitos de compra.");
    }
  };
  useEffect(() => {
    void Promise.all([
      refresh(),
      loadReceipts(),
      loadProducts(),
      loadTopProducts(),
      loadCategories(),
    ]);
  }, []);
  useEffect(() => {
    if (page === "estadisticas")
      void Promise.all([
        loadStatistics(statisticsRange),
        loadProductInsights(),
        loadCategoryAnalytics(statisticsRange),
      ]);
  }, [page, statisticsRange]);
  useEffect(() => {
    if (page === "estadisticas" && analysisSection === "habitos")
      void loadBasketInsights();
  }, [page, analysisSection]);
  useEffect(() => {
    if (page === "configuracion")
      void getJson<DataHealth>("/api/data-health")
        .then(setDataHealth)
        .catch(() => setMessage("No se ha podido cargar la salud de datos."));
  }, [page]);
  useEffect(() => {
    const query = searchQuery.trim();
    let active = true;
    setSearchResults(null);
    if (!query) return;
    const timer = window.setTimeout(() => {
      void getJson<SearchResults>(`/api/search?q=${encodeURIComponent(query)}`)
        .then((results) => {
          if (active) setSearchResults(results);
        })
        .catch(() => {
          if (active) setMessage("No se ha podido buscar.");
        });
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [searchQuery]);

  const showReceipt = async (id: number) => {
    try {
      setSelectedReceipt(await getJson<ReceiptDetail>(`/api/receipts/${id}`));
      setPage("compras");
    } catch {
      setMessage("No se ha podido abrir el ticket.");
    }
  };
  const showProduct = async (id: number) => {
    try {
      setSelectedProduct(
        await getJson<ProductAnalytics>(`/api/products/${id}/analytics`),
      );
      setPage("productos");
    } catch {
      setMessage("No se ha podido abrir el producto.");
    }
  };
  const uploadPdf = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setMessage("Importando PDF…");
    try {
      const response = await fetch("/api/receipts/import", {
        method: "POST",
        body: formData,
      });
      const result = (await response.json()) as {
        receipt_id?: number;
        duplicate?: boolean;
        warnings?: string[];
        detail?: string;
      };
      if (!response.ok)
        throw new Error(result.detail ?? "No se ha podido importar el PDF.");
      await Promise.all([
        refresh(),
        loadReceipts(),
        loadProducts(),
        loadTopProducts(),
      ]);
      setMessage(
        result.duplicate
          ? "Este PDF ya estaba importado."
          : result.warnings?.length
            ? "Ticket importado. Revisa los avisos detectados."
            : "Ticket importado correctamente.",
      );
      if (result.receipt_id) await showReceipt(result.receipt_id);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "No se ha podido importar el PDF.",
      );
    } finally {
      event.target.value = "";
    }
  };
  const runImport = async () => {
    setMessage("Buscando tickets nuevos…");
    try {
      const response = await fetch("/api/import/run", { method: "POST" });
      const result = (await response.json()) as
        | ImportStatus
        | { detail?: string };
      if (!response.ok)
        throw new Error(
          "detail" in result ? result.detail : "La búsqueda ha fallado.",
        );
      setImportStatus(result as ImportStatus);
      await Promise.all([
        refresh(),
        loadReceipts(),
        loadProducts(),
        loadTopProducts(),
      ]);
      setMessage("Búsqueda terminada.");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "La búsqueda ha fallado.",
      );
    }
  };
  const reprocessReceipt = async (id: number) => {
    setMessage("Reprocesando ticket…");
    try {
      const response = await fetch(`/api/receipts/${id}/reprocess`, {
        method: "POST",
      });
      const result = (await response.json()) as { detail?: string };
      if (!response.ok)
        throw new Error(
          result.detail ?? "No se ha podido reprocesar el ticket.",
        );
      await Promise.all([
        refresh(),
        loadReceipts(),
        loadProducts(),
        loadTopProducts(),
        showReceipt(id),
      ]);
      setMessage("Ticket reprocesado correctamente.");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "No se ha podido reprocesar el ticket.",
      );
    }
  };
  const mergeProduct = async (sourceId: number, targetId: number) => {
    setMessage("Uniendo productos…");
    try {
      const response = await fetch(`/api/products/${sourceId}/merge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_product_id: targetId }),
      });
      const result = (await response.json()) as {
        product_id?: number;
        target_name?: string;
        detail?: string;
      };
      if (!response.ok || !result.product_id)
        throw new Error(
          result.detail ?? "No se han podido unir los productos.",
        );
      await Promise.all([
        loadProducts(),
        loadTopProducts(),
        showProduct(result.product_id),
      ]);
      setMessage(`Producto unido a ${result.target_name}.`);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "No se han podido unir los productos.",
      );
    }
  };
  const renameProduct = async (id: number, name: string) => {
    setMessage("Guardando nombre…");
    try {
      const response = await fetch(`/api/products/${id}/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const result = (await response.json()) as {
        product_id?: number;
        name?: string;
        detail?: string;
      };
      if (!response.ok || !result.product_id)
        throw new Error(
          result.detail ?? "No se ha podido renombrar el producto.",
        );
      await Promise.all([
        loadProducts(),
        loadTopProducts(),
        showProduct(result.product_id),
      ]);
      setMessage(`Producto renombrado a ${result.name}.`);
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "No se ha podido renombrar el producto.",
      );
    }
  };
  const setProductCategory = async (id: number, categoryId: number | null) => {
    try {
      const response = await fetch(`/api/products/${id}/category`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category_id: categoryId }),
      });
      const result = (await response.json()) as {
        category?: ProductSummary["category"];
        detail?: string;
      };
      if (!response.ok)
        throw new Error(
          result.detail ?? "No se ha podido guardar la categoría.",
        );
      setSelectedProduct((current) =>
        current?.id === id
          ? { ...current, category: result.category ?? null }
          : current,
      );
      await Promise.all([
        loadProducts(),
        loadCategories(),
        loadCategoryAnalytics(statisticsRange),
      ]);
      setMessage("Categoría actualizada.");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "No se ha podido guardar la categoría.",
      );
    }
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Saltar al contenido
      </a>
      <aside className="sidebar">
        <div className="brand">
          <span>R</span>
          <strong>RitaCart</strong>
        </div>
        <nav aria-label="Navegación principal">
          {(
            [
              ["inicio", "Inicio"],
              ["compras", "Compras"],
              ["productos", "Productos"],
              ["estadisticas", "Análisis"],
              ["configuracion", "Ajustes"],
            ] as const
          ).map(([id, label]) => (
            <button
              className={page === id ? "nav-item active" : "nav-item"}
              key={id}
              aria-current={page === id ? "page" : undefined}
              onClick={() => {
                setPage(id);
                setSearchQuery("");
              }}
            >
              {label}
            </button>
          ))}
        </nav>
        <p className="sidebar-note">RitaCart 2.0.0 · Datos locales.</p>
      </aside>
      <main className="content" id="main-content" tabIndex={-1}>
        <section className="global-search">
          <label htmlFor="global-search">Buscar productos o tickets</label>
          <input
            id="global-search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Producto, alias, tienda o fecha"
          />
          {searchResults && (
            <SearchPanel
              results={searchResults}
              onProduct={(id) => {
                setSearchQuery("");
                void showProduct(id);
              }}
              onReceipt={(id) => {
                setSearchQuery("");
                void showReceipt(id);
              }}
            />
          )}
        </section>
        {message && (
          <p className="notice" role="status">
            {message}
          </p>
        )}
        {page === "inicio" && (
          <Home
            overview={overview}
            topProducts={topProducts}
            loading={loading}
            error={loadError}
            onRetry={refresh}
            onShowReceipt={showReceipt}
            onShowProduct={showProduct}
          />
        )}
        {page === "compras" && (
          <Purchases
            receipts={receipts}
            state={receiptsState}
            onRetry={loadReceipts}
            selected={selectedReceipt}
            onSelect={showReceipt}
            onUpload={uploadPdf}
            onReprocess={reprocessReceipt}
          />
        )}
        {page === "productos" && (
          <Products
            products={products}
            state={productsState}
            onRetry={loadProducts}
            categories={categories}
            selected={selectedProduct}
            onSelect={showProduct}
            onMerge={mergeProduct}
            onRename={renameProduct}
            onCategoryChange={setProductCategory}
          />
        )}
        {page === "estadisticas" && (
          <>
            <header className="analysis-header">
              <p className="eyebrow">Tu histórico</p>
              <h1>Análisis</h1>
              <p>Explora cómo cambian tus compras con el tiempo.</p>
            </header>
            <nav className="analysis-nav" aria-label="Secciones de análisis">
              {(
                [
                  ["gastos", "Gastos"],
                  ["categorias", "Categorías"],
                  ["precios", "Precios"],
                  ["habitos", "Hábitos"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  className={analysisSection === id ? "active" : ""}
                  aria-current={analysisSection === id ? "page" : undefined}
                  onClick={() => setAnalysisSection(id)}
                >
                  {label}
                </button>
              ))}
            </nav>
            {analysisSection === "habitos" ? (
              <Habits
                data={basketInsights}
                error={habitsError}
                onShowProduct={showProduct}
              />
            ) : (
              <Statistics
                section={analysisSection}
                error={analysisError}
                pricesError={pricesError}
                categoriesError={categoriesError}
                data={statistics}
                insights={productInsights}
                categoryData={categoryAnalytics}
                range={statisticsRange}
                onRangeChange={setStatisticsRange}
                topProducts={topProducts}
                onShowProduct={showProduct}
              />
            )}
          </>
        )}
        {page === "configuracion" && (
          <Configuration
            status={importStatus}
            health={dataHealth}
            onRun={runImport}
          />
        )}
      </main>
    </div>
  );
}
