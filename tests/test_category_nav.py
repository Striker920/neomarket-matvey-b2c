import pytest
from uuid import uuid4
from datetime import datetime, timezone
from src.models.category import Category
from src.models.product import Product


def _create_category(
    db_session,
    name: str = None,
    parent_id: str = None,
    category_id: str = None,
) -> Category:
    """Хелпер для создания тестовой категории."""
    cat = Category(
        id=category_id or str(uuid4()),
        name=name or f"Category {uuid4()}",
        slug=f"cat-{uuid4()}",
        parent_id=parent_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(cat)
    db_session.commit()
    return cat


def _create_product(
    db_session,
    category_id: str,
    product_id: str = None,
) -> Product:
    """Хелпер для создания тестового товара."""
    product = Product(
        id=product_id or str(uuid4()),
        title=f"Product {uuid4()}",
        category_id=category_id,
        status="MODERATED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(product)
    db_session.commit()
    return product


class TestCategoryNav:

    def test_category_tree_returns_nested_structure(self, client, db_session):
        """Дерево собирается из плоского списка в вложенную структуру."""
        root = _create_category(db_session, name="Electronics", category_id="root")
        child1 = _create_category(db_session, name="Phones", parent_id="root", category_id="child1")
        child2 = _create_category(db_session, name="Laptops", parent_id="root", category_id="child2")
        grandchild = _create_category(db_session, name="Smartphones", parent_id="child1", category_id="grandchild")
        
        response = client.get("/api/v1/categories/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        # Должен быть 1 корень
        assert len(data) == 1
        assert data[0]["id"] == "root"
        assert data[0]["name"] == "Electronics"
        
        # У корня 2 ребёнка
        children = data[0]["children"]
        assert len(children) == 2
        children_ids = {c["id"] for c in children}
        assert "child1" in children_ids
        assert "child2" in children_ids
        
        # У child1 есть grandchild
        phones = next(c for c in children if c["id"] == "child1")
        assert len(phones["children"]) == 1
        assert phones["children"][0]["id"] == "grandchild"
        
        # У child2 нет детей
        laptops = next(c for c in children if c["id"] == "child2")
        assert len(laptops["children"]) == 0

    def test_breadcrumbs_return_path_from_root(self, client, db_session):
        """Цепочка хлебных крошек от корня до категории."""
        root = _create_category(db_session, name="Electronics", category_id="root")
        child = _create_category(db_session, name="Phones", parent_id="root", category_id="child")
        grandchild = _create_category(db_session, name="Smartphones", parent_id="child", category_id="grandchild")
        
        response = client.get("/api/v1/breadcrumbs?category_id=grandchild")
        
        assert response.status_code == 200
        data = response.json()
        breadcrumbs = data["breadcrumbs"]
        
        # Путь: root → child → grandchild
        assert len(breadcrumbs) == 3
        assert breadcrumbs[0]["id"] == "root"
        assert breadcrumbs[0]["name"] == "Electronics"
        assert breadcrumbs[1]["id"] == "child"
        assert breadcrumbs[1]["name"] == "Phones"
        assert breadcrumbs[2]["id"] == "grandchild"
        assert breadcrumbs[2]["name"] == "Smartphones"

    def test_breadcrumbs_by_product_id(self, client, db_session):
        """Хлебные крошки для товара."""
        root = _create_category(db_session, name="Electronics", category_id="root")
        child = _create_category(db_session, name="Phones", parent_id="root", category_id="child")
        product = _create_product(db_session, category_id="child", product_id="prod-1")
        
        response = client.get("/api/v1/breadcrumbs?product_id=prod-1")
        
        assert response.status_code == 200
        data = response.json()
        breadcrumbs = data["breadcrumbs"]
        
        assert len(breadcrumbs) == 2
        assert breadcrumbs[0]["id"] == "root"
        assert breadcrumbs[1]["id"] == "child"

    def test_unknown_category_returns_404(self, client, db_session):
        """Несуществующая категория → 404."""
        response = client.get("/api/v1/breadcrumbs?category_id=non-existent")
        
        assert response.status_code == 404
        data = response.json()
        # ✅ Адаптировано под кастомный обработчик (без 'detail')
        assert data["code"] == "NOT_FOUND"

    def test_orphan_node_returns_422(self, client, db_session):
        """Сломанная иерархия (orphan node) → 422."""
        orphan = _create_category(
            db_session,
            name="Orphan",
            parent_id="missing-parent",
            category_id="orphan"
        )
        
        response = client.get("/api/v1/categories/tree")
        
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "ORPHAN_NODE"
        assert data["category_id"] == "orphan"
        assert data["missing_parent_id"] == "missing-parent"

    def test_orphan_node_in_breadcrumbs_returns_422(self, client, db_session):
        """Orphan node при запросе breadcrumbs → 422."""
        orphan = _create_category(
            db_session,
            name="Orphan",
            parent_id="missing-parent",
            category_id="orphan"
        )
        
        response = client.get("/api/v1/breadcrumbs?category_id=orphan")
        
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "ORPHAN_NODE"

    def test_ambiguous_params_returns_400(self, client, db_session):
        """Оба параметра (category_id и product_id) одновременно → 400."""
        response = client.get("/api/v1/breadcrumbs?category_id=cat-1&product_id=prod-1")
        
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "AMBIGUOUS_PARAMS"

    def test_missing_params_returns_400(self, client, db_session):
        """Ни одного параметра → 400."""
        response = client.get("/api/v1/breadcrumbs")
        
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "MISSING_PARAMS"

    def test_category_details_returns_info(self, client, db_session):
        """GET /categories/{id} возвращает детали категории."""
        cat = _create_category(db_session, name="Test Category", category_id="test-cat")
        
        response = client.get("/api/v1/categories/test-cat")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-cat"
        assert data["name"] == "Test Category"

    def test_category_details_not_found_returns_404(self, client, db_session):
        """GET /categories/{id} для несуществующей → 404."""
        response = client.get("/api/v1/categories/non-existent")
        
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "NOT_FOUND"