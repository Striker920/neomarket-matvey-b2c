from src.services.b2b_client import b2b_client
from src.schemas.catalog import CatalogProductCard
import httpx


class SimilarProductsService:
    def get_similar_products(
        self,
        product_id: str,
        category_id: str = None,
        limit: int = 8,
        offset: int = 0
    ) -> list[CatalogProductCard] | None:
        """
        US-CAT-04: Выборка похожих товаров.
        
        Возвращает plain array CatalogProductCard[] (по спецификации OpenAPI).
        """
        if not category_id:
            try:
                product = b2b_client.get_product_by_id(product_id)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
            if not product:
                return None
            category_id = product.get("category", {}).get("id")
            if not category_id:
                return []

        b2b_data = b2b_client.get_products(
            limit=limit + 1,
            offset=0,
            category=category_id
        )

        items = []
        for item in b2b_data.get("items", []):
            if str(item.get("id")) == str(product_id):
                continue

            skus = item.get("skus", [])
            
            # min_price: минимальная цена среди SKU с active_quantity > 0
            min_price = min(
                (s.get("price", 0) for s in skus if s.get("active_quantity", 0) > 0),
                default=0
            )
            
            # has_stock: есть ли хотя бы один SKU с active_quantity > 0
            has_stock = any(s.get("active_quantity", 0) > 0 for s in skus)
            
            # images: список URL изображений (исправлен баг)
            images = []
            for s in skus:
                if s.get("image"):
                    images.append(s["image"])
            
            if not images and item.get("images"):
                for img in item["images"]:
                    if isinstance(img, dict):
                        url = img.get("url")
                        if url:
                            images.append(url)
                    elif isinstance(img, str):
                        images.append(img)

            items.append(CatalogProductCard(
                id=item.get("id"),
                name=item.get("title"),  # title → name
                min_price=min_price,      # price → min_price
                has_stock=has_stock,      # in_stock → has_stock
                images=images             # image → images (list)
            ))

            if len(items) >= limit:
                break

        return items


similar_products_service = SimilarProductsService()