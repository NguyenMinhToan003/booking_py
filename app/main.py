from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.common.exceptions.exception_handlers import register_exception_handlers
from app.common.middlewares.csrf_middleware import CsrfMiddleware
from app.configs.settings import get_settings
from app.database import models_registry  # noqa: F401  -- đăng ký toàn bộ model trước mapper configure

settings = get_settings()


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}" if route.tags else route.name


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CsrfMiddleware)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_STR)
