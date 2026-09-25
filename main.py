import math
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Fast Simon Assessment API")


class Product(BaseModel):
    id: int
    name: str
    category: str
    price: float


PRODUCTS: list[Product] = [
    Product(id=1, name="Running Shoes", category="shoes", price=120.0),
    Product(id=2, name="Cotton T-Shirt", category="apparel", price=25.0),
    Product(id=3, name="Leather Belt", category="accessories", price=45.0),
    Product(id=4, name="Winter Jacket", category="apparel", price=150.0),
]


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/products")
def get_products(
    category: Optional[str] = None,
    max_price: Optional[float] = Query(default=None),
):
    results = PRODUCTS

    if category:
        results = [p for p in results if p.category == category.lower()]

    if max_price is not None:
        if not math.isfinite(max_price) or max_price < 0:
            raise HTTPException(
                status_code=400,
                detail="max_price must be a non-negative number.",
            )
        results = [p for p in results if p.price <= max_price]

    return {"count": len(results), "data": results}
