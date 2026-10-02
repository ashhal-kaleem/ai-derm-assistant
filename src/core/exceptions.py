from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class DermAssistException(Exception):
    """Base exception for all DermAssist domain & service errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, error_type: str = "internal_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type


class ModelInferenceError(DermAssistException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error_type="inference_failed")


class InvalidImageError(DermAssistException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, error_type="invalid_image")


class ResourceNotFoundError(DermAssistException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, error_type="not_found")


def register_exception_handlers(app: FastAPI) -> None:
    """Register RFC 9457 Problem Details standard error handlers."""
    
    @app.exception_handler(DermAssistException)
    async def handle_dermassist_exception(request: Request, exc: DermAssistException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"urn:dermassist:error:{exc.error_type}",
                "title": exc.error_type.replace("_", " ").title(),
                "status": exc.status_code,
                "detail": exc.message,
                "instance": str(request.url.path),
            },
        )
