from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint

from app.api.auth import router as auth_router
from app.api.exercises import router as exercises_router
from app.api.health import router as health_router
from app.api.listening import router as listening_router
from app.api.telegram import router as telegram_router
from app.api.upload_limit import UploadLimit
from app.database import Database
from app.services.auth import ServiceError, sync_emergency
from app.settings import Settings


async def http_error(_request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, HTTPException):
        raise error
    codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 413: "FILE_TOO_LARGE"}
    return JSONResponse(
        status_code=error.status_code,
        content={"error": codes.get(error.status_code, "HTTP_ERROR")},
        headers=error.headers,
    )


async def service_error(_request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, ServiceError):
        raise error
    headers = {"Cache-Control": "no-store"}
    if error.retry_after is not None:
        headers["Retry-After"] = str(error.retry_after)
    return JSONResponse(
        status_code=error.status, content={"error": error.code}, headers=headers
    )


async def validation_error(_request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, RequestValidationError):
        raise error
    return JSONResponse(status_code=422, content={"error": "VALIDATION_ERROR"})


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = Database(configuration)
        application.state.database = database
        try:
            await run_in_threadpool(sync_emergency, database, configuration)
            yield
        finally:
            await run_in_threadpool(database.close)

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = configuration
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(ServiceError, service_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(exercises_router)
    app.include_router(listening_router)
    app.include_router(telegram_router)
    app.add_middleware(UploadLimit, maximum=configuration.upload_max_bytes)

    @app.middleware("http")
    async def no_store(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
