from fastapi import APIRouter, Cookie, Depends, Response

from app.common.abstracts.auth_port import AuthContext, AuthPrincipal
from app.configs.settings import get_settings
from app.modules.auth.auth_strategy import SessionAuthStrategy
from app.modules.auth.dependencies import (
    SESSION_COOKIE_NAME,
    MissingSessionError,
    get_auth_context,
    get_auth_service,
    get_current_user,
    get_session_strategy,
)
from app.modules.auth.schemas import LoginRequestDTO, SessionInfoDTO
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE_PATH = "/"
settings = get_settings()


def _set_session_cookie(response: Response, raw_session_id: str, expires_at) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_session_id,
        httponly=True,
        secure=settings.ENV != "development",
        samesite="lax",
        path=SESSION_COOKIE_PATH,
        expires=expires_at,
    )


@router.post("/login", response_model=SessionInfoDTO)
async def login(
    body: LoginRequestDTO,
    response: Response,
    context: AuthContext = Depends(get_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
    strategy: SessionAuthStrategy = Depends(get_session_strategy),
) -> SessionInfoDTO:
    user = await auth_service.authenticate_credentials(body.email, body.password)
    result = await strategy.sign_in(str(user.id), user.email, context)
    _set_session_cookie(response, result.raw_session_id, result.expires_at)
    return SessionInfoDTO(expires_at=result.expires_at)


@router.post("/refresh", response_model=SessionInfoDTO)
async def refresh(
    response: Response,
    context: AuthContext = Depends(get_auth_context),
    strategy: SessionAuthStrategy = Depends(get_session_strategy),
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> SessionInfoDTO:
    if not session_id:
        raise MissingSessionError()
    result = await strategy.renew(session_id, context)
    _set_session_cookie(response, result.raw_session_id, result.expires_at)
    return SessionInfoDTO(expires_at=result.expires_at)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    strategy: SessionAuthStrategy = Depends(get_session_strategy),
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> None:
    if session_id:
        await strategy.sign_out(session_id)
    response.delete_cookie(SESSION_COOKIE_NAME, path=SESSION_COOKIE_PATH)


@router.post("/logout-all", status_code=204)
async def logout_all(
    response: Response,
    current_user: AuthPrincipal = Depends(get_current_user),
    strategy: SessionAuthStrategy = Depends(get_session_strategy),
) -> None:
    await strategy.revoke_all(current_user.subject_id)
    response.delete_cookie(SESSION_COOKIE_NAME, path=SESSION_COOKIE_PATH)
