from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER = "x-requested-with"
CSRF_HEADER_VALUE = "XMLHttpRequest"


class CsrfMiddleware(BaseHTTPMiddleware):
    """Session dùng cookie, browser tự gửi kèm mọi request -> cần chống CSRF.
    Yêu cầu header X-Requested-With trên mọi method không an toàn, kể cả route public —
    header này trình duyệt không tự thêm được qua cross-site form submit, chỉ JS same-origin
    (hoặc CORS cho phép) mới set được. Đúng pattern CsrfGuard của Nest, không cần CSRF token
    riêng vì session cookie không mang giá trị tự verify được (opaque, không phải JWT).
    """

    async def dispatch(self, request: Request, call_next):
        if request.method in UNSAFE_METHODS:
            header_value = request.headers.get(CSRF_HEADER, "")
            if header_value != CSRF_HEADER_VALUE:
                return JSONResponse(
                    status_code=403,
                    content={
                        "statusCode": 403,
                        "error": "CsrfError",
                        "message": f"Missing or invalid {CSRF_HEADER} header",
                        "path": request.url.path,
                    },
                )
        return await call_next(request)
