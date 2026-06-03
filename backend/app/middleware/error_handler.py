"""
Global error handler — barcha kutilmagan xatolarni ushlaydi
"""
import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global exception handler middleware.
    Barcha kutilmagan xatolarni ushlaydi va JSON formatda qaytaradi.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(
                f"Kutilmagan xato: {request.method} {request.url.path} | "
                f"Error: {str(e)} | Traceback: {traceback.format_exc()}"
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Serverda ichki xato yuz berdi. Iltimos, keyinroq urinib ko'ring.",
                    "error_code": "INTERNAL_ERROR",
                },
            )
