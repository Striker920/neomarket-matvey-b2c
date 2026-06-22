# feat(us-cart-03): корзина покупателя с исправлениями арбитра

## 🎯 Цель

Реализовать корзину покупателя с поддержкой гостевого режима (X-Session-Id), авторизованного режима (JWT), обогащением из B2B и merge при логине.

## 🔍 Контекст (исправления по фидбэку арбитра)

Были выявлены 4 несоответствия спецификации:

> 1. Обновление позиции реализовано методом PUT вместо PATCH
> 2. Параметр пути `{item_id}` вместо `{sku_id}`
> 3. DELETE возвращает 204 вместо 200 с телом CartResponse
> 4. Отсутствует endpoint POST /cart/merge для слияния гостевой корзины

## ✅ Что исправлено

| # | Было | Стало |
|---|------|-------|
| 1 | `PUT /items/{item_id}` | `PATCH /items/{sku_id}` |
| 2 | `{item_id}` в update/delete | `{sku_id}` |
| 3 | `DELETE /items/{item_id}` → 204 | `DELETE /items/{sku_id}` → 200 с CartResponse |
| 4 | Отсутствует `POST /cart/merge` | Добавлен endpoint |
| 5 | `POST /items` → 201 | `POST /items` → 200 |

## 📂 Изменения в файлах

### `src/api/cart.py`
- `PUT` → `PATCH` с параметром `{sku_id}`
- `DELETE /items/{sku_id}` возвращает `200 + CartResponse`
- Добавлен endpoint `POST /cart/merge`
- Исправлена функция `get_identity`: теперь читает оба идентификатора (JWT + X-Session-Id)

### `src/services/cart_service.py`
- Методы `update_item` и `remove_item` теперь принимают `sku_id` вместо `item_id`
- Метод `merge_guest_cart` использует `MAX(guest, auth)` quantity при конфликте

### `tests/test_cart.py`
- Обновлены тесты под новую сигнатуру (PATCH, sku_id, 200)
- Добавлен тест `test_guest_cart_merged_on_login`

## 🧪 Тестовое покрытие

| # | Тест | Статус | Описание |
|---|------|:------:|----------|
| 1 | `test_add_sku_increments_quantity_if_already_in_cart` | ✅ | Повторное добавление SKU суммирует quantity |
| 2 | `test_get_cart_enriched_with_b2b_data` | ✅ | GET /cart обогащает данные из B2B |
| 3 | `test_unavailable_sku_shown_with_reason` | ✅ | Недоступный SKU с unavailable_reason |
| 4 | `test_guest_cart_works_with_session_id` | ✅ | Гостевая корзина через X-Session-Id |
| 5 | `test_missing_identity_returns_400` | ✅ | 400 без идентификаторов |
| 6 | `test_update_quantity` | ✅ | PATCH /items/{sku_id} |
| 7 | `test_remove_item` | ✅ | DELETE /items/{sku_id} → 200 |
| 8 | `test_clear_cart` | ✅ | DELETE /cart → 204 |
| 9 | `test_guest_cart_merged_on_login` | ✅ | Merge гостевой корзины (MAX quantity) |

**Результат:** `9 passed` ✅

## 📐 ADR: Идентификация гостевой корзины

### Рассмотренные варианты
1. **X-Session-Id заголовок** — простота, совместимость с мобильными клиентами
2. **Cookie** — автоматическая передача, но не работает для mobile
3. **Временный JWT** — безопасность, но избыточная сложность

### Решение — **X-Session-Id заголовок**

**Обоснование:**
1. **Совместимость с мобильными клиентами**: легко генерируется UUID, передаётся в заголовке
2. **Риск подделки**: минимальный — корзина не содержит критичных данных, при merge требуется двойная проверка (JWT + session_id)

## ✅ Соответствие DoD

| Требование | Статус |
|---|:---:|
| Соответствие канон-flow `flows/b2c-cart-flows.md#b2c-8-cart` | ✅ |
| `add_sku_increments_quantity_if_already_in_cart` | ✅ |
| `get_cart_enriched_with_b2b_data` | ✅ |
| `unavailable_sku_shown_with_reason` | ✅ |
| `guest_cart_merged_on_login` | ✅ |
| Соответствие OpenAPI `b2c/cart/openapi.yaml` | ✅ |
| ADR в описании PR | ✅ |
| 4+ pytest покрывают все сценарии канона | ✅ (9 тестов) |

## 🔗 Связанные задачи

- **US-CART-03** — корзина покупателя (основная задача)
- **US-B2B-07** — каталог товаров для B2C (источник данных для обогащения)
