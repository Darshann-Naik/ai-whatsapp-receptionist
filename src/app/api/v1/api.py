# src/app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import whatsapp
from app.api.v1.endpoints import admin # Add this import
api_router = APIRouter()
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])