import logging

from app.common.audit.models import AuditActionType
from app.common.audit.repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Gọi tay tại điểm cần, không có interceptor/decorator tự động — chỉ audit thao tác
    thật sự cần (theo yêu cầu thực dụng cho y tế, khác cơ chế @AuditAction tự động của Nest).

    actor_label/actor_role là snapshot TẠI THỜI ĐIỂM hành động (vd "BS. Nguyễn Văn A", "doctor")
    — không phải FK, lấy từ AuthPrincipal/User lúc gọi. Không bao giờ lưu tên bệnh nhân
    (target_patient_id chỉ là ID) — audit log không được chứa PHI, chỉ tham chiếu.

    Lỗi khi ghi audit KHÔNG BAO GIỜ được làm fail nghiệp vụ chính — log error, swallow
    exception. Audit là nghĩa vụ compliance, không phải invariant nghiệp vụ.

    Dùng:
        await audit.log_write(
            actor_id, "BS. Nguyễn Văn A", "doctor", "booking.cancel", "booking", booking_id,
            old_value={"status": "confirmed"}, new_value={"status": "cancelled"},
        )
        await audit.log_read(
            actor_id, "BS. Nguyễn Văn A", "doctor", "patient_record.view", "patient_record",
            record_id, target_patient_id=patient_id, ip=request_ip,
        )
    """

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def log_write(
        self,
        actor_id: str,
        actor_label: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        *,
        success: bool = True,
        target_patient_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
    ) -> None:
        await self._safe_insert(
            actor_id,
            actor_label,
            actor_role,
            action,
            AuditActionType.WRITE,
            resource_type,
            resource_id,
            success,
            target_patient_id,
            ip,
            user_agent,
            old_value,
            new_value,
        )

    async def log_read(
        self,
        actor_id: str,
        actor_label: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        *,
        success: bool = True,
        target_patient_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """PHI access log: ai XEM dữ liệu bệnh nhân nào. Gọi ở điểm đọc dữ liệu nhạy cảm,
        không phải mọi GET — chỉ khi resource chứa PHI thật (hồ sơ bệnh án, kết quả khám)."""
        await self._safe_insert(
            actor_id,
            actor_label,
            actor_role,
            action,
            AuditActionType.READ,
            resource_type,
            resource_id,
            success,
            target_patient_id,
            ip,
            user_agent,
            None,
            None,
        )

    async def _safe_insert(
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
        try:
            await self.repo.insert(
                actor_id,
                actor_label,
                actor_role,
                action,
                action_type,
                resource_type,
                resource_id,
                success,
                target_patient_id,
                ip,
                user_agent,
                old_value,
                new_value,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Audit log failed (action=%s, resource=%s/%s): %s", action, resource_type, resource_id, exc
            )
