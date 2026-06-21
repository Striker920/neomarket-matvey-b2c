# fix(us-cat-04): приведён ответ /similar к спецификации OpenAPI

## 🔧 Исправления по фидбэку арбитров

### Проблема
1. Response возвращал wrapper `{items, total_count, ...}` вместо plain array
2. Поля не соответствовали `CatalogProductCard`: `title`, `price`, `in_stock` вместо `name`, `min_price`, `has_stock`, `images`
3. Лимит `limit` был ограничен 20 вместо 50
4. Баг с fallback для images: `item['images'][0]` мог вернуть list вместо строки

### Решение

| Было | Стало |
|------|-------|
| `{items: [...], total_count, limit, offset}` | `CatalogProductCard[]` (plain array) |
| `title` | `name` |
| `price` | `min_price` |
| `in_stock` | `has_stock` |
| `image` (string) | `images` (array of URLs) |
| `limit` max 20 | `limit` max 50 |

## 📂 Изменения в файлах

### `src/schemas/catalog.py`
- Добавлена схема `CatalogProductCard` с полями: `id`, `name`, `min_price`, `has_stock`, `images`
- Сохранены существующие схемы: `ProductShortListResponse`, `FacetsResponse` и др.

### `src/services/similar_products_service.py`
- Возвращает `list[CatalogProductCard]` вместо dict-wrapper
- Исправлен баг с fallback для images: корректная обработка dict и list
- Маппинг полей: `title → name`, `price → min_price`, `in_stock → has_stock`, `image → images`

### `src/api/similar_products.py`
- `response_model=List[CatalogProductCard]` (plain array)
- `limit` max 50 (по спецификации OpenAPI)

### `tests/test_similar_products.py`
- Проверка plain array (не wrapper)
- Проверка полей `CatalogProductCard`
- 4 теста покрывают все сценарии канона

## 🧪 Тестовое покрытие

| # | Тест | Статус |
|---|------|:------:|
| 1 | `test_similar_returns_up_to_8_from_same_category` | ✅ |
| 2 | `test_empty_category_returns_200_empty_list` | ✅ |
| 3 | `test_unknown_product_returns_404` | ✅ |
| 4 | `test_limit_parameter_works` | ✅ |

**Результат:** `4 passed` ✅
