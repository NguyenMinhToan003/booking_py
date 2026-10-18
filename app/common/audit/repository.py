from sqlalchemy.ext.asyncio import AsyncSession

from app.common.audit.models import AuditActionType, AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        actor_id: str,
        actor_label: str,
        actor_role: str,
        action: str,
        action_type: AuditActionType,
        resource_type: str,
        resource_id: str | None,
        success: bool,
        target_patient_id: str | None,
        ip: str | None,
        user_agent: str | None,
        old_value: dict | None,
        new_value: dict | None,
    ) -> None:
        event = AuditEvent(
            actor_id=actor_id,
            actor_label=actor_label,
            actor_role=actor_role,
            action=action,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            target_patient_id=target_patient_id,
            ip=ip,
            user_agent=user_agent,
            old_value=old_value,
            new_value=new_value,
        )
        self.session.add(event)
        await self.session.commit()
