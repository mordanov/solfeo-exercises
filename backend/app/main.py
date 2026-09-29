from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.health import router as health_router
from app.database import Database
from app.settings import Settings


async def http_error(_request: Request, error: Exception) -> JSONResponse:
    if not isinstance(error, HTTPException):
        raise error
    codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    return JSONResponse(
        status_code=error.status_code,
        content={"error": codes.get(error.status_code, "HTTP_ERROR")},
        headers=error.headers,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = Database(configuration)
        application.state.database = database
        try:
            yield
        finally:
            await run_in_threadpool(database.close)

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.add_exception_handler(HTTPException, http_error)
    app.include_router(health_router)
    return app
