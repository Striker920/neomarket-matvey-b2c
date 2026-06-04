## Описание
Ключевые особенности:
- Идемпотентность через заголовок Idempotency-Key
- All-or-nothing резервирование через B2B сервис
- Фиксация цен в OrderItem на момент покупки (исторический снимок)
- Поддержка опционального items_snapshot для защиты от гонок
- Обработка недоступности B2B (503) и частичных сбоев резервирования (409)
- Возврат 422 при невалидной корзине

## Соответствие OpenAPI спецификации
Реализация полностью соответствует b2c/openapi.yaml из neomarket-protocols:
- Путь: POST /api/v1/orders
- Заголовок: Idempotency-Key (обязательный)
- Схема запроса: OrderCreateRequest с полями address_id, payment_method_id, опционально items_snapshot
- Схема ответа: OrderResponse с address, payment_method, status_history, delivery_cost, total
- Коды ответа: 201 (создан), 409 (конфликт idempotency или резерв), 422 (невалидная корзина), 503 (B2B недоступен)

## ADR: Хранение идемпотентности

Контекст: Необходимо гарантировать, что повторные запросы checkout с одинаковым Idempotency-Key не создают дублирующие заказы и не списывают деньги дважды.

Рассмотренные альтернативы:
1. Уникальный индекс на idempotency_key в таблице orders. Просто в реализации, но при race condition (два одновременных запроса) один из них упадет с IntegrityError, которую нужно перехватывать.
2. Отдельная таблица-кэш ключей. Более гибкая, позволяет хранить метаданные, но требует дополнительной таблицы и усложняет поддержку.
3. Redis для хранения ключей. Быстро и масштабируемо, но требует дополнительной инфраструктуры и не гарантирует персистентность при падении.

Выбрано: Уникальный индекс на idempotency_key в таблице orders.

Критерии выбора:
- Поведение при race condition: При параллельных запросах с одинаковым ключом один из них завершится ошибкой IntegrityError, которая перехватывается в сервисе. После этого выполняется повторный запрос к БД для получения существующего заказа, что гарантирует корректный ответ клиенту.
- Сложность реализации: Минимальная. Достаточно добавить уникальное ограничение на колонку и обработать IntegrityError. Не требует дополнительных таблиц или внешней инфраструктуры.

## Лог тестов (DoD)
platform win32 -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-ORD-01
plugins: anyio-4.13.0
collected 4 items                                                                                                  

tests/test_checkout_flow.py::test_checkout_creates_paid_order_with_fixed_prices PASSED                       [ 25%]
tests/test_checkout_flow.py::test_partial_reserve_failure_returns_409 PASSED                                 [ 50%]
tests/test_checkout_flow.py::test_idempotency_returns_existing_order PASSED                                  [ 75%]
tests/test_checkout_flow.py::test_b2b_unavailable_returns_503 PASSED                                         [100%]

