from __future__ import annotations

import json
from datetime import datetime
from typing import Literal
from decimal import Decimal

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
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
from .services.importer import ReceiptImportError, ReceiptImportService

router = APIRouter(prefix="/api")


class ProductMergeRequest(BaseModel):
    target_product_id: int


class ProductRenameRequest(BaseModel):
    name: str


class ProductCategoryRequest(BaseModel):
    category_id: int | None


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
        "imported_at": receipt.imported_at.isoformat(),
        "item_count": len(receipt.items),
    }
    if detail:
        payload["items"] = [_item_payload(item) for item in receipt.items]
        payload["vat_breakdown"] = [_vat_payload(vat) for vat in receipt.vat_breakdown]
        payload["parser_warnings"] = json.loads(receipt.parser_warnings or "[]")
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
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="El archivo está vacío")
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


@router.get("/analytics/statistics", tags=["analytics"])
def get_global_statistics(
    request: Request, range: Literal["3m", "6m", "1y", "all"] = "6m"
) -> dict[str, object]:
    with request.app.state.session_factory() as session:
        return global_statistics(session, range, request.app.state.settings.timezone)


@router.get("/overview", tags=["overview"])
def overview(request: Request) -> dict[str, object]:
    now = datetime.now()
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
