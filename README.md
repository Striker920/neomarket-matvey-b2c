# fix(us-cart-03): корзина покупателя — исправления по OpenAPI

## 🎯 Цель

Исправить 6 замечаний арбитров по US-CART-03: привести пути роутеров, схемы событий и корзины, а также возвращаемые типы endpoint'ов к спецификации `b2c/openapi.yaml`.

## 🔍 Контекст

Корзина — место, где покупатель собирает заказ. Гость не должен терять добавленные товары при логине. Цены должны обновляться при каждом просмотре — а не храниться в корзине. Резерв товара происходит только при checkout, а не при добавлении.

## 🔧 Исправления по фидбэку арбитров

| # | Было | Стало |
|---|------|-------|
| 1 | `POST /api/v1/events/product` | ✅ `POST /api/v1/b2b/events` |
| 2 | `event: str`, плоские поля | ✅ `event_type`, `idempotency_key`, `occurred_at`, `payload` |
| 3 | `CartResponse` без `items_count`, `subtotal`, `is_valid` | ✅ Все поля добавлены |
| 4 | `title`, `price`, `available` | ✅ `name`, `unit_price`, `is_available` + `line_total`, `available_quantity` |
| 5 | POST/PATCH возвращают dict | ✅ Возвращают `CartResponse` |
| 6 | `/api/v1/products` (seller, требует JWT) | ✅ `/api/v1/public/products` (public, только X-Service-Key) |

## ✅ Что реализовано

### Endpoints корзины

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/cart/` | Получить корзину с обогащением из B2B |
| POST | `/api/v1/cart/items` | Добавить SKU (увеличивает quantity если уже есть) |
| PATCH | `/api/v1/cart/items/{sku_id}` | Обновить количество |
| DELETE | `/api/v1/cart/items/{sku_id}` | Удалить позицию |
| DELETE | `/api/v1/cart/` | Очистить корзину → 204 |
| POST | `/api/v1/cart/merge` | Merge гостевой корзины при логине |

### Endpoints событий от B2B

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/b2b/events` | Приём событий PRODUCT_BLOCKED, PRODUCT_DELETED, SKU_OUT_OF_STOCK |

### Идентификация
- **Авторизованный**: JWT с `user_id` (заголовок `Authorization: Bearer ...`)
- **Гость**: `X-Session-Id` заголовок (UUID)

### Обогащение из B2B
- При каждом GET /cart вызывается B2B `GET /api/v1/public/products?ids=...`
- Цены и наличие берутся из B2B, не хранятся в корзине
- `unavailable_reason` вычисляется: `OUT_OF_STOCK`, `PRODUCT_DELETED`

### Merge при логине
- Логика: MAX(guest, auth) по SKU
- Если SKU есть в обеих корзинах — берём максимальное количество
- Гостевая корзина очищается после merge

### IDOR-защита
- Позиции корзины привязаны к `user_id` или `session_id`
- Нельзя изменить/удалить чужую позицию

### Lazy reserve
- Корзина НЕ резервирует товар при добавлении
- Резерв происходит только при checkout (US-CART-04)

## 📂 Изменения в файлах

### `src/api/events.py`
- `prefix="/api/v1/b2b"` вместо `"/api/v1/events"`
- `@router.post("/events")` вместо `@router.post("/product")`
- Итоговый путь: `POST /api/v1/b2b/events` (по `b2c/openapi.yaml:758`)

### `src/schemas/event.py`
- Полная переработка схемы `B2BEvent`:
  - `event_type: EventType` вместо `event: str`
  - `idempotency_key: str` (обязательное)
  - `occurred_at: datetime` (обязательное)
  - `payload: Union[EventProductRef, EventSkuStock, EventPriceChanged]`

### `src/schemas/cart.py`
- `CartItemResponse`:
  - `title` → `name`
  - `price` → `unit_price`
  - `available` → `is_available`
  - Добавлены `line_total`, `available_quantity`
- `CartResponse`:
  - Добавлены `items_count: int`, `subtotal: int`, `is_valid: bool`

### `src/services/b2b_client.py`
- Заменён URL: `/api/v1/products` → `/api/v1/public/products`
- Теперь вызов идёт с `X-Service-Key` без JWT

### `src/services/cart_service.py`
- `get_cart()` возвращает `CartResponse` с обязательными полями
- Обогащение использует публичный endpoint B2B
- Форматирование `CartItemResponse` с новыми именами полей

### `src/api/cart.py`
- `POST /api/v1/cart/items` возвращает `CartResponse`
- `PATCH /api/v1/cart/items/{sku_id}` возвращает `CartResponse`
- `DELETE /api/v1/cart/items/{sku_id}` возвращает `CartResponse`

### `tests/test_cart.py`
- Обновлены тесты под новый формат ответов
- Переименованы поля в assert'ах
- Добавлены проверки новых обязательных полей

## 🧪 Тестовое покрытие

| # | Тест | Статус | Описание |
|---|------|:------:|----------|
| 1 | `test_add_sku_increments_quantity_if_already_in_cart` | ✅ | Повторное добавление → quantity++ |
| 2 | `test_get_cart_enriched_with_b2b_data` | ✅ | GET /cart обогащает из B2B |
| 3 | `test_unavailable_sku_shown_with_reason` | ✅ | Недоступный SKU с unavailable_reason |
| 4 | `test_update_quantity` | ✅ | PATCH обновляет количество |
| 5 | `test_guest_cart_works_with_session_id` | ✅ | Гость с X-Session-Id |
| 6 | `test_missing_identity_returns_400` | ✅ | Без идентификатора → 400 |
| 7 | `test_remove_item` | ✅ | Удаление позиции |
| 8 | `test_clear_cart` | ✅ | Очистка корзины → 204 |
| 9 | `test_guest_cart_merged_on_login` | ✅ | Merge: MAX(guest, auth) |

**Результат:** `9 passed` ✅

### Запуск тестов
```powershell
cd C:\neomarket-matvey-b2c-feature-us-cart-03-cart
Remove-Item -Force test.db -ErrorAction SilentlyContinue
C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests/test_cart.py -v
