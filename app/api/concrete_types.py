"""API router for concrete type schemas and definitions."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from app.engine.type_schemas import TYPE_SCHEMAS, get_type_schema, list_type_schemas

router = APIRouter(prefix="/api/concrete-types", tags=["concrete-types"])


@router.get("")
@router.get("/")
def get_types_list():
    """List all concrete types with summary information."""
    return list_type_schemas()


@router.get("/schemas")
def get_all_schemas() -> Dict[str, Any]:
    """Return all concrete type schemas keyed by type name."""
    return TYPE_SCHEMAS


@router.get("/{concrete_type}/schema")
def get_schema(concrete_type: str) -> Dict[str, Any]:
    """Return the explicit parameter schema for a specific concrete type."""
    try:
        return get_type_schema(concrete_type)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown concrete type '{concrete_type}'. Available types: {list(TYPE_SCHEMAS.keys())}"
        )


@router.get("/{concrete_type}")
def get_type_detail(concrete_type: str) -> Dict[str, Any]:
    """Return the schema and metadata for a specific concrete type."""
    try:
        return get_type_schema(concrete_type)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown concrete type '{concrete_type}'. Available types: {list(TYPE_SCHEMAS.keys())}"
        )
