from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from ..dependencies import get_store
from ..store import ItemStore


router = APIRouter(prefix="/items", tags=["items"])


class ItemInput(BaseModel):
    content: str


class ItemOutput(BaseModel):
    id: int
    content: str


@router.get("", response_model=list[ItemOutput])
def list_items(
    limit: int = Query(default=10, ge=1, le=100),
    store: Annotated[ItemStore, Depends(get_store)],
):
    return store.list_items(limit)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_item_route(
    item: ItemInput,
    store: Annotated[ItemStore, Depends(get_store)],
):
    return store.create_item(item.content)
