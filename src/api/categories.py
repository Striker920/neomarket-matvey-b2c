from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from src.database import get_db
from src.services.category_service import CategoryService, OrphanNodeError
from src.schemas.categories import CategoryNode, CategoryDetails, BreadcrumbsResponse

router = APIRouter(prefix="/api/v1", tags=["Categories"])


@router.get("/categories/tree", response_model=List[CategoryNode])
def get_category_tree(
    db: Session = Depends(get_db),
):
    """
    Получить дерево категорий.
    
    Если обнаружена сломанная иерархия (orphan node) → 422.
    """
    service = CategoryService(db)
    try:
        return service.get_category_tree()
    except OrphanNodeError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ORPHAN_NODE",
                "message": str(e),
                "category_id": e.category_id,
                "missing_parent_id": e.missing_parent_id,
            }
        )


@router.get("/categories/{category_id}", response_model=CategoryDetails)
def get_category_details(
    category_id: str,
    db: Session = Depends(get_db),
):
    """
    Получить детали категории.
    404 если категория не найдена.
    """
    service = CategoryService(db)
    details = service.get_category_details(category_id)
    if not details:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_FOUND",
                "message": f"Category {category_id} not found"
            }
        )
    return details


@router.get("/breadcrumbs", response_model=BreadcrumbsResponse)
def get_breadcrumbs(
    category_id: str = Query(None, description="ID категории"),
    product_id: str = Query(None, description="ID товара"),
    db: Session = Depends(get_db),
):
    """
    Получить хлебные крошки от корня до категории/товара.
    
    Принимает РОВНО ОДИН параметр: category_id ИЛИ product_id.
    Оба одновременно → 400.
    Ни одного → 400.
    """
    # Проверка параметров
    if category_id and product_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "AMBIGUOUS_PARAMS",
                "message": "Provide either category_id or product_id, not both"
            }
        )
    
    if not category_id and not product_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_PARAMS",
                "message": "Provide either category_id or product_id"
            }
        )
    
    service = CategoryService(db)
    
    try:
        if category_id:
            breadcrumbs = service.get_breadcrumbs_by_category(category_id)
        else:
            breadcrumbs = service.get_breadcrumbs_by_product(product_id)
    except OrphanNodeError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ORPHAN_NODE",
                "message": str(e),
                "category_id": e.category_id,
                "missing_parent_id": e.missing_parent_id,
            }
        )
    
    if breadcrumbs is None:
        if category_id:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NOT_FOUND",
                    "message": f"Category {category_id} not found"
                }
            )
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "NOT_FOUND",
                    "message": f"Product {product_id} not found"
                }
            )
    
    return BreadcrumbsResponse(breadcrumbs=breadcrumbs)