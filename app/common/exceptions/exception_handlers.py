import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

from app.common.exceptions.domain_exception import DomainException
from app.database.concurrency import OptimisticConcurrencyError

logger = logging.getLogger(__name__)

# Postgres SQLSTATE: 55P03 lock_not_available, 40P01 deadlock_detected, 40001 serialization_failure.
# Cả 3 là lỗi tạm thời do tranh chấp lock — client nên retry nguyên request, không phải lỗi hệ thống.
RETRYABLE_PG_CODES = {"55P03", "40P01", "40001"}


def _build_body(
    status_code: int,
    error: str,
    message: str,
    path: str,
    code: str | None = None,
    details: dict | None = None,
) -> dict:
    body = {
        "statusCode": status_code,
        "error": error,
        "message": message,
        "path": path,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if code is not None:
        body["code"] = code
    if details is not None:
        body["details"] = details
    return body


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_body(
            exc.status_code,
            type(exc).__name__,
            exc.message,
            request.url.path,
            exc.code,
            exc.details,
        ),
    )


async def optimistic_concurrency_handler(
    request: Request, exc: OptimisticConcurrencyError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=_build_body(
            409,
            "OptimisticConcurrencyError",
            str(exc),
            request.url.path,
            code="OPTIMISTIC_CONCURRENCY_CONFLICT",
            details={
                "entity": exc.entity_name,
                "id": str(exc.entity_id),
                "retryable": True,
            },
        ),
    )


async def db_error_handler(request: Request, exc: DBAPIError) -> JSONResponse:
    pg_code = getattr(getattr(exc, "orig", None), "sqlstate", None)
    if pg_code in RETRYABLE_PG_CODES:
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": "1"},
            content=_build_body(
                503,
                "ConcurrencyUnavailable",
                "The operation could not acquire a database lock; retry the complete request",
                request.url.path,
                code="DATABASE_CONCURRENCY_RETRY",
                details={"retryable": True},
            ),
        )
    logger.error("Unhandled DB error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content=_build_body(
            500, "DatabaseError", "Internal server error", request.url.path
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(
        OptimisticConcurrencyError, optimistic_concurrency_handler
    )
    app.add_exception_handler(DBAPIError, db_error_handler)
