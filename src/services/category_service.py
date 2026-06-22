from sqlalchemy.orm import Session
from src.models.category import Category
from src.models.product import Product
from src.schemas.categories import CategoryNode, CategoryDetails, BreadcrumbItem
from typing import List, Optional


class OrphanNodeError(Exception):
    """Выбрасывается при обнаружении сломанной иерархии (orphan node)."""
    def __init__(self, category_id: str, missing_parent_id: str):
        self.category_id = category_id
        self.missing_parent_id = missing_parent_id
        super().__init__(
            f"Orphan node detected: category {category_id} references missing parent {missing_parent_id}"
        )


class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_category_tree(self) -> List[CategoryNode]:
        """
        Построить дерево категорий из плоского списка.
        
        Если обнаружен orphan node → OrphanNodeError (422)
        """
        all_categories = self.db.query(Category).all()
        
        if not all_categories:
            return []
        
        # Создаём словарь для быстрого поиска
        categories_by_id = {c.id: c for c in all_categories}
        
        # Проверяем orphan nodes
        for cat in all_categories:
            if cat.parent_id and cat.parent_id not in categories_by_id:
                raise OrphanNodeError(cat.id, cat.parent_id)
        
        # Строим дерево
        nodes_by_id = {
            c.id: CategoryNode(
                id=c.id,
                name=c.name,
                slug=c.slug,
                parent_id=c.parent_id,
                children=[]
            )
            for c in all_categories
        }
        
        roots = []
        for cat in all_categories:
            node = nodes_by_id[cat.id]
            if cat.parent_id is None:
                roots.append(node)
            else:
                parent_node = nodes_by_id[cat.parent_id]
                parent_node.children.append(node)
        
        # Сортируем по имени для стабильности
        self._sort_tree(roots)
        return roots

    def _sort_tree(self, nodes: List[CategoryNode]):
        """Рекурсивная сортировка дерева по имени."""
        nodes.sort(key=lambda n: n.name)
        for node in nodes:
            if node.children:
                self._sort_tree(node.children)

    def get_category_details(self, category_id: str) -> Optional[CategoryDetails]:
        """Получить детали категории по ID."""
        cat = self.db.query(Category).filter(Category.id == category_id).first()
        if not cat:
            return None
        return CategoryDetails(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            parent_id=cat.parent_id,
        )

    def get_breadcrumbs_by_category(self, category_id: str) -> Optional[List[BreadcrumbItem]]:
        """
        Получить хлебные крошки от корня до категории.
        
        Возвращает None если категория не найдена (→ 404).
        Выбрасывает OrphanNodeError при сломанной иерархии (→ 422).
        """
        cat = self.db.query(Category).filter(Category.id == category_id).first()
        if not cat:
            return None
        
        # Проверяем целостность иерархии
        self._check_hierarchy_integrity(cat)
        
        # Идём вверх по parent_id до корня
        path = []
        current = cat
        visited = set()
        
        while current is not None:
            if current.id in visited:
                raise OrphanNodeError(current.id, "cycle_detected")
            visited.add(current.id)
            
            path.append(BreadcrumbItem(
                id=current.id,
                name=current.name,
                slug=current.slug,
            ))
            
            if current.parent_id is None:
                break
            
            current = self.db.query(Category).filter(
                Category.id == current.parent_id
            ).first()
            
            if current is None:
                raise OrphanNodeError(visited.pop(), "missing_parent")
        
        # Разворачиваем: от корня к текущей категории
        path.reverse()
        return path

    def get_breadcrumbs_by_product(self, product_id: str) -> Optional[List[BreadcrumbItem]]:
        """
        Получить хлебные крошки для товара.
        
        Возвращает None если товар не найден (→ 404).
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return None
        
        if not product.category_id:
            return []
        
        return self.get_breadcrumbs_by_category(product.category_id)

    def _check_hierarchy_integrity(self, category: Category):
        """Проверить целостность иерархии от категории до корня."""
        current = category
        visited = set()
        
        while current is not None:
            if current.id in visited:
                raise OrphanNodeError(current.id, "cycle_detected")
            visited.add(current.id)
            
            if current.parent_id is None:
                break
            
            parent = self.db.query(Category).filter(
                Category.id == current.parent_id
            ).first()
            
            if parent is None:
                raise OrphanNodeError(current.id, current.parent_id)
            
            current = parent