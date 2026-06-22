# feat(us-cat-05): навигация по категориям

## 🎯 Цель

Реализовать навигацию по каталогу: дерево категорий, детали категории и хлебные крошки. Хлебные крошки — это GPS маркетплейса: убрать их, и покупатель потерян.

## 🔍 Контекст

Покупатель ориентируется в магазине через боковое меню и хлебные крошки. Без навигации — каталог плоский список, покупатель не понимает, где он находится.

## ✅ Что реализовано

### Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/categories/tree` | Дерево категорий (вложенная структура) |
| GET | `/api/v1/categories/{id}` | Детали категории |
| GET | `/api/v1/breadcrumbs` | Хлебные крошки |

### Breadcrumbs
- Принимает **ровно один** параметр: `category_id` ИЛИ `product_id`
- Оба одновременно → **400 Bad Request** (`AMBIGUOUS_PARAMS`)
- Ни одного → **400 Bad Request** (`MISSING_PARAMS`)
- Несуществующая категория/товар → **404 Not Found**
- Сломанная иерархия (orphan node) → **422 Unprocessable Entity** (`ORPHAN_NODE`)

### Response (GET /categories/tree)
```json
[
  {
    "id": "root",
    "name": "Electronics",
    "slug": "electronics",
    "parent_id": null,
    "children": [
      {
        "id": "child1",
        "name": "Phones",
        "parent_id": "root",
        "children": [
          {
            "id": "grandchild",
            "name": "Smartphones",
            "parent_id": "child1",
            "children": []
          }
        ]
      }
    ]
  }
]
Тесты
platform win32 -- Python 3.12.3, pytest-7.4.3, pluggy-1.6.0 -- C:\Users\matvey_chertovikov\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\US-CAT-05\US-B2C-01
plugins: anyio-3.7.1, asyncio-0.21.1
asyncio: mode=Mode.STRICT
collected 10 items                                                                                              

tests/test_category_nav.py::TestCategoryNav::test_breadcrumbs_by_product_id PASSED                        [ 30%]
tests/test_category_nav.py::TestCategoryNav::test_orphan_node_in_breadcrumbs_returns_422 PASSED           [ 60%]
tests/test_category_nav.py::TestCategoryNav::test_ambiguous_params_returns_400 PASSED                     [ 70%]
tests/test_category_nav.py::TestCategoryNav::test_missing_params_returns_400 PASSED                       [ 80%]
tests/test_category_nav.py::TestCategoryNav::test_category_details_returns_info PASSED                    [ 90%]
tests/test_category_nav.py::TestCategoryNav::test_category_details_not_found_returns_404 PASSED           [100%]
