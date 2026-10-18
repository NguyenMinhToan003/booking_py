from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.audit.repository import AuditRepository
from app.common.audit.service import AuditService
from app.database.session import get_db


def get_audit_service(session: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(AuditRepository(session))
