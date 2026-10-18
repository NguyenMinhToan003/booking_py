"""Import mọi model của mọi module để đăng ký vào Base.metadata trước khi mapper
configure. Bắt buộc cho forward-ref relationship (vd User.roles -> "Role") hoạt động
đúng lúc app khởi động — không phải lúc import module users hay rbac riêng lẻ.
main.py import file này trước khi app nhận request đầu tiên."""

from app.common.audit.models import AuditEvent  # noqa: F401
from app.modules.auth.models import AuthSession  # noqa: F401
from app.modules.rbac.models import Permission, Role  # noqa: F401
from app.modules.users.models import User  # noqa: F401
