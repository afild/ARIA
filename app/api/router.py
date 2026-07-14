"""
Corporate Standard Module: router
This module is part of the ARIA core framework.
"""
from fastapi import APIRouter
from app.api.alerts import router as alerts_router
from app.api.credit import router as credit_router
from app.api.graph import router as graph_router
from app.api.chat import router as chat_router
from app.api.system import router as system_router

api_router = APIRouter()

# Inclui os sub-routers
api_router.include_router(alerts_router)
api_router.include_router(credit_router)
api_router.include_router(graph_router)
api_router.include_router(chat_router)
api_router.include_router(system_router)
