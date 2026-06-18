from fastapi import APIRouter

from app.api.v1.bookings import router as bookings_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(bookings_router)
