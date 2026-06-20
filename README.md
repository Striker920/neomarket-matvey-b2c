# Исправление US-ORD-01: плоская структура ошибок и CartValidationResponse

## Описание
Реализованы финальные исправления для полного соответствия спецификациям `b2c/openapi.yaml` и `b2b/openapi.yaml`.

## Соответствие канон-флоу

### Happy path
- ✅ **checkout_creates_paid_order_with_fixed_prices** — заказ создаётся в статусе PAID с актуальными ценами из B2B
- ✅ **idempotency_returns_existing_order** — повторный вызов с тем же Idempotency-Key возвращает существующий заказ

### Unhappy path
- ✅ **partial_reserve_failure_returns_409** — частичная ошибка резерва → 409 с плоским `{code, message}`
- ✅ **b2b_unavailable_returns_503** — недоступность B2B/Cart → 503
- ✅ **empty_cart_returns_422_with_validation_response** — пустая корзина → 422 с `CartValidationResponse`

## Соответствие OpenAPI

### B2B (b2b/openapi.yaml)
- ✅ Путь reserve: `POST /api/v1/inventory/reserve` (строка 928)
- ✅ ReserveRequest содержит `order_id` (строки 1706-1715)
- ✅ ReserveResponse: `{order_id, status, reserved_at}` (строки 1717-1723)

### B2C (b2c/openapi.yaml)
- ✅ Плоская структура ошибок: `{code, message}` без обёртки `detail` (строки 870-879)
- ✅ CartValidationResponse: `{is_valid, cart, issues}` (строки 672-676)
- ✅ OrderCreateRequest принимает `address_id` и `payment_method_id` (строки 1241-1262)

## Внесённые исправления

### 1. Глобальный exception handler (`src/main.py`)
Добавлен handler, переупаковывающий `HTTPException.detail` в плоский `{code, message}` согласно `b2c/openapi.yaml:870-879`.

### 2. CartValidationResponse для пустой корзины (`src/api/v1/orders.py`)
Вместо `{code: "CART_INVALID"}` теперь возвращается `{is_valid: false, cart: [], issues: [...]}` согласно `b2c/openapi.yaml:672-676`.

### 3. Исправлена синтаксическая ошибка (`src/api/v1/orders.py`)
В блоке `except B2BUnavailableError` отсутствовал `raise HTTPException(...)` — код не компилировался.

### 4. Убран rollback после commit (`src/services/checkout_service.py`)
`db.rollback()` после `db.commit()` откатывал транзакцию и терял заказ. Заменено на корректную обработку `IntegrityError`.

### 5. Исправлен тест идемпотентности (`tests/test_checkout_flow.py`)
`resp2` не был определён — добавлен второй запрос.

### 6. Обновлены тесты
`response.json()["detail"]["code"]` → `response.json()["code"]` (плоская структура).

## ADR: Структура ошибок API

**Контекст:** B2C OpenAPI требует плоский `{code, message}` на верхнем уровне, а FastAPI по умолчанию оборачивает в `{detail: {...}}`.

**Рассмотренные альтернативы:**
1. **Изменять каждый `raise HTTPException`** — дублирование, риск пропустить место
2. **Глобальный exception handler** — централизация, единая точка правды
3. **Прямой возврат JSONResponse** — работает, но дублирует логику

**Выбрано:** Вариант 2 — глобальный exception handler.

**Критерии:**
- **Соответствие спецификации:** Плоский `{code, message}` согласно b2c openapi
- **Централизация:** Все ошибки обрабатываются в одном месте

## Лог тестов (DoD)
platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-ORD-01
plugins: anyio-4.13.0
collected 5 items                                                                      

tests/test_checkout_flow.py::test_checkout_creates_paid_order_with_fixed_prices PASSED [ 20%]
tests/test_checkout_flow.py::test_partial_reserve_failure_returns_409 PASSED     [ 40%]
tests/test_checkout_flow.py::test_idempotency_returns_existing_order PASSED      [ 60%]
tests/test_checkout_flow.py::test_b2b_unavailable_returns_503 PASSED             [ 80%]
tests/test_checkout_flow.py::test_empty_cart_returns_422_with_validation_response PASSED [100%]
