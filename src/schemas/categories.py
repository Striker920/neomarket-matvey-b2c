from pydantic import BaseModel, Field
from typing import Optional, List


class CategoryNode(BaseModel):
    """Узел дерева категорий."""
    id: str
    name: str
    slug: Optional[str] = None
    parent_id: Optional[str] = None
    children: List["CategoryNode"] = []
    
    model_config = {"from_attributes": True}


# Обновляем рекурсивную модель
CategoryNode.model_rebuild()


class CategoryDetails(BaseModel):
    """Детали категории."""
    id: str
    name: str
    slug: Optional[str] = None
    parent_id: Optional[str] = None
    
    model_config = {"from_attributes": True}


class BreadcrumbItem(BaseModel):
    """Элемент хлебных крошек."""
    id: str
    name: str
    slug: Optional[str] = None


class BreadcrumbsResponse(BaseModel):
    """Ответ хлебных крошек — массив от корня до текущей категории."""
    breadcrumbs: List[BreadcrumbItem]
    
    model_config = {"from_attributes": True}