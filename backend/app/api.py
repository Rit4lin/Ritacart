from __future__ import annotations

from datetime import datetime
from typing import Literal
from decimal import Decimal

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from .models import Category, Product, Receipt, ReceiptItem, ReceiptVat
from .analytics.products import list_products as product_list
from .analytics.products import merge_products, product_analytics, product_insights, rename_product, top_products
from .analytics.statistics import global_statistics
from .analytics.statistics import _local_now
from .analytics.categories import category_analytics
from .analytics.basket import basket_insights
from .services.data_tools import csv_export, data_health, decimal_or_none, decode_parser_warnings, search
from .services.importer import ReceiptImportError, ReceiptImportService
from .services.pdf import MAX_RECEIPT_PDF_BYTES

router = APIRouter(prefix="/api")


class ProductMergeRequest(BaseModel):
    target_product_id: int


class ProductRenameRequest(BaseModel):
    name: str


class ProductCategoryRequest(BaseModel):
    category_id: int | None


class BulkCategoryRequest(BaseModel):
    product_ids: list[int]
    category_id: int | None


class ReceiptItemEditRequest(BaseModel):
    product_id: int | None = None
    quantity: str | None = None
    unit_price: str | None = None
    price_per_kg: str | None = None
    total_price: str | None = None


def _money(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _item_payload(item: ReceiptItem) -> dict[str, object]:
    return {
        "id": item.id,
        "product_id": item.product_id,
        "raw_name": item.raw_name,
        "quantity": _money(item.quantity),
        "unit": item.unit,
        "unit_price": _money(item.unit_price),
        "price_per_kg": _money(item.price_per_kg),
        "total_price": _money(item.total_price),
        "raw_text": item.raw_text,
    }


def _vat_payload(vat: ReceiptVat) -> dict[str, object]:
    return {
        "rate": _money(vat.rate),
        "taxable_base": _money(vat.taxable_base),
        "tax_amount": _money(vat.tax_amount),
    }


def _receipt_payload(receipt: Receipt, detail: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": receipt.id,
        "store": receipt.store.name,
        "purchased_at": receipt.purchased_at.isoformat(),
        "total": _money(receipt.total),
        "source_filename": receipt.source_filename,
        "source": "email" if receipt.source_message_id else "manual",
        "imported_at": receipt.imported_at.isoformat(),
        "item_count": len(receipt.items),
        "needs_review": not receipt.items or bool(decode_parser_warnings(receipt.parser_warnings)),
    }
    if detail:
        payload["items"] = [_item_payload(item) for item in receipt.items]
        payload["vat_breakdown"] = [_vat_payload(vat) for vat in receipt.vat_breakdown]
        payload["parser_warnings"] = decode_parser_warnings(receipt.parser_warnings)
        payload["source_extracted_text"] = receipt.source_extracted_text
    return payload


def _importer(request: Request) -> ReceiptImportService:
    return request.app.state.importer


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/import/status", tags=["import"])
def import_status(request: Request) -> dict[str, object]:
    return _importer(request).get_status()


@router.post("/import/run", tags=["import"])
def run_import(request: Request) -> dict[str, object]:
    importer = _importer(request)
    try:
        importer.run_imap_import()
    except ReceiptImportError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return importer.get_status()


@router.post("/receipts/import", status_code=status.HTTP_201_CREATED, tags=["receipts"])
async def import_receipt_pdf(request: Request, file: UploadFile = File(...)) -> dict[str, object]:
    try:
        content = await file.read(MAX_RECEIPT_PDF_BYTES + 1)
    finally:
        await file.close()
    if not content:
        raise HTTPException(status_code=422, detail="El archivo está vacío")
    if len(content) > MAX_RECEIPT_PDF_BYTES:
        raise HTTPException(status_code=413, detail="El PDF supera el límite de 20 MB")
    try:
        result = _importer(request).import_pdf(content, file.filename)
    except ReceiptImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "receipt_id": result.receipt_id,
        "imported": result.imported,
        "duplicate": result.duplicate,
        "warnings": result.warnings,
    }


@router.get("/receipts", tags=["receipts"])
def list_receipts(request: Request) -> list[dict[str, object]]:
    with request.app.state.session_factory() as session:
        receipts = session.scalars(
            select(Receipt)
            .options(selectinload(Receipt.items), selectinload(Receipt.store))
            .order_by(Receipt.purchased_at.desc())
        ).all()
        return [_receipt_payload(receipt) for receipt in receipts]


@router.get("/receipts/{receipt_id}", tags=["receipts"])
def get_receipt(receipt_id: int, request: Request) -> dict[str, object]:
    with request.app.state.session_factory() as session:
        receipt = session.scalar(
            select(Receipt)
            .options(
                selectinload(Receipt.items),
                selectinload(Receipt.store),
                selectinload(Receipt.vat_breakdown),
            )
            .where(Receipt.id == receipt_id)
        )
        if receipt is None:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return _receipt_payload(receipt, detail=True)


@router.post("/receipts/{receipt_id}/reprocess", tags=["receipts"])
def reprocess_receipt(receipt_id: int, request: Request) -> dict[str, object]:
    try:
        result = _importer(request).reprocess_receipt(receipt_id)
    except ReceiptImportError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(exc) == "Ticket no encontrado"
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"receipt_id": result.receipt_id, "warnings": result.warnings}


@router.patch("/receipts/{receipt_id}/items/{item_id}", tags=["receipts"])
def edit_receipt_item(receipt_id: int, item_id: int, payload: ReceiptItemEditRequest, request: Request) -> dict[str, object]:
    try:
        values = {field: decimal_or_none(getattr(payload, field), field) for field in ("quantity", "unit_price", "price_per_kg", "total_price")}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with request.app.state.session_factory() as session:
        item = session.scalar(select(ReceiptItem).where(ReceiptItem.id == item_id, ReceiptItem.receipt_id == receipt_id))
        if item is None:
            raise HTTPException(status_code=404, detail="Línea no encontrada")
        if payload.product_id is not None and session.get(Product, payload.product_id) is None:
            raise HTTPException(status_code=422, detail="Producto no encontrado")
        if payload.product_id is not None:
            item.product_id = payload.product_id
        for field, value in values.items():
            if getattr(payload, field) is not None:
                setattr(item, field, value)
        session.commit()
        return _item_payload(item)


@router.get("/receipts/{receipt_id}/pdf", tags=["receipts"])
def get_receipt_pdf(receipt_id: int, request: Request) -> FileResponse:
    with request.app.state.session_factory() as session:
        receipt = session.get(Receipt, receipt_id)
        if receipt is None:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        path = request.app.state.settings.app_data_dir / "receipts" / f"{receipt.source_file_hash}.pdf"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="PDF original no encontrado")
        return FileResponse(path, media_type="application/pdf", filename=receipt.source_filename)


@router.get("/products", tags=["products"])
def list_products(request: Request) -> list[dict[str, object]]:
    with request.app.state.session_factory() as session:
        return product_list(session)


@router.get("/categories", tags=["categories"])
def list_categories(request: Request) -> list[dict[str, object]]:
    with request.app.state.session_factory() as session:
        categories = session.scalars(
            select(Category).options(selectinload(Category.products)).order_by(Category.sort_order)
        ).all()
        return [
            {"id": category.id, "name": category.name, "slug": category.slug, "product_count": len(category.products)}
            for category in categories
        ]


@router.patch("/products/{product_id}/category", tags=["products"])
def set_product_category(
    product_id: int, payload: ProductCategoryRequest, request: Request
) -> dict[str, object]:
    with request.app.state.session_factory() as session:
        product = session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        category = session.get(Category, payload.category_id) if payload.category_id is not None else None
        if payload.category_id is not None and category is None:
            raise HTTPException(status_code=422, detail="Categoría no encontrada")
        product.category_id = category.id if category else None
        session.commit()
        return {"product_id": product.id, "category": {"id": category.id, "name": category.name, "slug": category.slug} if category else None}


@router.patch("/products/categories", tags=["products"])
def set_products_category(payload: BulkCategoryRequest, request: Request) -> dict[str, object]:
    ids = set(payload.product_ids)
    if not ids:
        raise HTTPException(status_code=422, detail="Selecciona al menos un producto")
    with request.app.state.session_factory() as session:
        products = session.scalars(select(Product).where(Product.id.in_(ids))).all()
        if len(products) != len(ids):
            raise HTTPException(status_code=422, detail="Uno o más productos no existen")
        if payload.category_id is not None and session.get(Category, payload.category_id) is None:
            raise HTTPException(status_code=422, detail="Categoría no encontrada")
        for product in products:
            product.category_id = payload.category_id
        session.commit()
        return {"updated_products": len(products)}


@router.get("/products/{product_id}/analytics", tags=["products"])
def get_product_analytics(product_id: int, request: Request) -> dict[str, object]:
    with request.app.state.session_factory() as session:
        analytics = product_analytics(session, product_id)
        if analytics is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        return analytics


@router.post("/products/{product_id}/merge", tags=["products"])
def merge_product(
    product_id: int,
    payload: ProductMergeRequest,
    request: Request,
) -> dict[str, object]:
    try:
        with request.app.state.session_factory() as session:
            merged = merge_products(session, product_id, payload.target_product_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if merged is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return merged


@router.post("/products/{product_id}/rename", tags=["products"])
def rename_product_endpoint(
    product_id: int,
    payload: ProductRenameRequest,
    request: Request,
) -> dict[str, object]:
    try:
        with request.app.state.session_factory() as session:
            renamed = rename_product(session, product_id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if renamed is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return renamed


@router.get("/analytics/products/top", tags=["analytics"])
def get_top_products(request: Request) -> list[dict[str, object]]:
    with request.app.state.session_factory() as session:
        return top_products(session)


@router.get("/analytics/products/insights", tags=["analytics"])
def get_product_insights(request: Request) -> dict[str, list[dict[str, object]]]:
    with request.app.state.session_factory() as session:
        return product_insights(session)


@router.get("/analytics/categories", tags=["analytics"])
def get_category_analytics(
    request: Request, range: Literal["3m", "6m", "1y", "all"] = "6m"
) -> dict[str, object]:
    with request.app.state.session_factory() as session:
        return category_analytics(session, range, _local_now(request.app.state.settings.timezone))


@router.get("/analytics/basket", tags=["analytics"])
def get_basket_insights(request: Request) -> dict[str, object]:
    with request.app.state.session_factory() as session:
        return basket_insights(session, _local_now(request.app.state.settings.timezone))


@router.get("/search", tags=["search"])
def global_search(request: Request, q: str = "") -> dict[str, list[dict[str, object]]]:
    with request.app.state.session_factory() as session:
        return search(session, q)


@router.get("/data-health", tags=["system"])
def get_data_health(request: Request) -> dict[str, int]:
    with request.app.state.session_factory() as session:
        return data_health(session)


@router.get("/export/{kind}.csv", tags=["export"])
def export_csv(kind: str, request: Request) -> Response:
    try:
        with request.app.state.session_factory() as session:
            content = csv_export(session, kind)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="ritacart-{kind}.csv"'})


@router.get("/analytics/statistics", tags=["analytics"])
def get_global_statistics(
    request: Request, range: Literal["3m", "6m", "1y", "all"] = "6m"
) -> dict[str, object]:
    with request.app.state.session_factory() as session:
        return global_statistics(session, range, request.app.state.settings.timezone)


@router.get("/overview", tags=["overview"])
def overview(request: Request) -> dict[str, object]:
    now = _local_now(request.app.state.settings.timezone)
    month_start = datetime(now.year, now.month, 1)
    with request.app.state.session_factory() as session:
        total, count = session.execute(select(func.sum(Receipt.total), func.count(Receipt.id))).one()
        month_total = session.scalar(
            select(func.sum(Receipt.total)).where(Receipt.purchased_at >= month_start)
        )
        latest = session.scalar(
            select(Receipt)
            .options(selectinload(Receipt.items), selectinload(Receipt.store))
            .order_by(Receipt.purchased_at.desc())
            .limit(1)
        )
        return {
            "total_spend": _money(total) or "0.00",
            "receipt_count": count,
            "current_month_spend": _money(month_total) or "0.00",
            "latest_receipt": _receipt_payload(latest) if latest else None,
        }
