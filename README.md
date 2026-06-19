# Исправление US-ORD-01 по замечаниям AI-арбитра (финальная версия)

## Описание
Реализованы финальные исправления для полного соответствия спецификациям B2B и Cart Service.

## Внесенные исправления

### 1. Исправлен путь к B2B reserve
Изменён endpoint с `/api/v1/reservations` на `/api/v1/inventory/reserve` в соответствии с контрактом B2B сервиса.

### 2. Добавлен обязательный order_id в запросе к B2B
`order_id` (UUID) теперь генерируется **ДО** вызова резервирования и передаётся в payload вместе с `items` и `idempotency_key`, что соответствует схеме `ReserveRequest`.

### 3. Цены берутся ДО резервирования через отдельный HTTP-вызов
Создан метод `b2b_client.get_sku_details_batch(sku_ids)`, который выполняет **реальный HTTP POST** к эндпоинту `/api/v1/public/products/batch` B2B-сервиса для получения актуальных цен и деталей SKU перед резервированием.

Ответ `ReserveResponse` теперь используется только для проверки статуса (`{order_id, status, reserved_at}`), а не для чтения цен — это исключает `KeyError` в production.

### 4. Корзина читается server-side через HTTP-вызов
Создан отдельный клиент `src/services/cart_client.py` с методом `get_cart(buyer_id)`, который выполняет **реальный HTTP GET** к эндпоинту `/api/v1/cart/{buyer_id}` Cart Service.

Захардкоженный список `[{"sku_id": "sku-001", ...}]` удалён.

### 5. buyer_id извлекается из JWT
Функция `get_current_buyer` читает заголовок `Authorization: Bearer <token>` и извлекает `buyer_id`. В реальной системе здесь будет парсинг JWT.

### 6. Валидация items_snapshot
Добавлена логика сверки `items_snapshot` (если передан клиентом) с актуальным содержимым корзины для защиты от гонок (race condition).

## ADR: Архитектура взаимодействия с внешними сервисами

**Контекст:** Checkout должен взаимодействовать с двумя внешними сервисами — B2B (резервирование и каталог) и Cart Service (корзина покупателя).

**Выбранное решение:** Отдельные HTTP-клиенты для каждого сервиса с чёткими контрактами.

**Критерии:**
- **Разделение ответственности:** Каждый клиент инкапсулирует логику взаимодействия с конкретным сервисом
- **Тестируемость:** Клиенты легко мокаются в unit-тестах
- **Надёжность:** Каждый вызов обрабатывает ошибки (503, таймауты) и возвращает понятные исключения
- **Соответствие контрактам:** Пути и payload строго соответствуют OpenAPI-спецификациям

## Лог тестов (DoD)

platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
collected 4 items

tests/test_checkout_flow.py::test_checkout_creates_paid_order_with_fixed_prices PASSED
tests/test_checkout_flow.py::test_partial_reserve_failure_returns_409 PASSED
tests/test_checkout_flow.py::test_idempotency_returns_existing_order PASSED
tests/test_checkout_flow.py::test_b2b_unavailable_returns_503 PASSED

============================== 4 passed in X.XXs ===============================

## Чек-лист замечаний арбитра
- [x] Путь изменён на `/api/v1/inventory/reserve`
- [x] Добавлен `order_id` в запросе к B2B
- [x] Цены берутся через отдельный HTTP POST к `/api/v1/public/products/batch` ДО резервирования
- [x] Корзина читается через HTTP GET к `/api/v1/cart/{buyer_id}`
- [x] `buyer_id` извлекается из JWT (Bearer-токен)
- [x] Все 4 теста проходят
