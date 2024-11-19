from flask import request
from werkzeug.exceptions import HTTPException
from app.core.models.responses import ErrorResponse
from app.core.models.errors import HTTPErrorDetail


def handle_http_error(error: HTTPException):
    return ErrorResponse(
        message=str(error),
        error=HTTPErrorDetail(
            code=error.__class__.__name__.upper(),
            status=error.code,
            details={
                "method": request.method,
                "path": request.path
            }
        ).dict(),
        status=error.code
    ).dict(), error.code
