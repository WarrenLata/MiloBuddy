from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import security, verify_firebase_token
from app.db.deps import get_db
from app.db.models import Category

router = APIRouter(
    prefix="/categories", tags=["categories"], dependencies=[Security(security)]
)


class CategoryOut(BaseModel):
    id: UUID
    name: str
    icon: str | None
    color_hex: str | None
    is_system: bool


class CreateCategoryRequest(BaseModel):
    name: str
    icon: str | None = None
    color_hex: str | None = None


@router.get("", response_model=list[CategoryOut], dependencies=[Security(security)])
async def list_categories(
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    result = await db.execute(
        select(Category)
        .where(or_(Category.user_id == user_uuid, Category.user_id.is_(None)))
        .order_by(Category.user_id.is_(None).desc(), Category.name.asc())
    )
    categories = result.scalars().all()
    return [
        CategoryOut(
            id=c.id,
            name=c.name,
            icon=c.icon,
            color_hex=c.color_hex,
            is_system=c.user_id is None,
        )
        for c in categories
    ]


@router.post("", response_model=CategoryOut, dependencies=[Security(security)])
async def create_category(
    req: CreateCategoryRequest,
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    name = req.name.strip()
    if len(name) > 50:
        raise HTTPException(status_code=400, detail="Name must be <= 50 characters")

    existing_result = await db.execute(
        select(Category)
        .where(Category.user_id == user_uuid, Category.name == name)
        .limit(1)
    )
    existing = existing_result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=409, detail="A category with the same name already exists"
        )

    category = Category(
        user_id=user_uuid,
        name=name,
        icon=req.icon,
        color_hex=req.color_hex,
        is_system=False,
    )
    db.add(category)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await db.refresh(category)
    return CategoryOut(
        id=category.id,
        name=category.name,
        icon=category.icon,
        color_hex=category.color_hex,
        is_system=category.user_id is None,
    )
