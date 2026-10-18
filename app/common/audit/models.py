import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.abstracts.base_model import Base


class AuditActionType(StrEnum):
    """read: ai XEM dữ liệu nhạy cảm (PHI access log — bắt buộc với hồ sơ y tế).
    write: ai TẠO/SỬA/HỦY — khác hẳn read vì có old_value/new_value để so sánh."""

    READ = "read"
    WRITE = "write"


class AuditEvent(Base):
    """Append-only — không có updated_at/version/deleted_at, không bao giờ sửa/xóa 1 dòng
    đã ghi. Chỉ ghi khi code tại điểm cần chủ động gọi AuditService.log(...) — không có
    interceptor/decorator tự động bắt mọi request, tránh audit noise cho thao tác không
    nhạy cảm (khác bản Nest gốc, đơn giản hơn theo yêu cầu thực dụng cho y tế).

    Thiết kế "enriched event" (xem research): actor được denormalize (actor_label/actor_role)
    vì audit phải đọc đúng danh tính TẠI THỜI ĐIỂM hành động, sống sót qua đổi tên/xóa user
    (giống AWS CloudTrail userIdentity). Patient/resource CHỈ lưu ID, không lưu tên — audit
    log không được chứa PHI, chỉ tham chiếu PHI; tên bệnh nhân lấy qua join lúc đọc/report."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # Snapshot tên+role lúc hành động — không FK, không tự update theo users sau này.
    # "BS. Nguyễn Văn A" vẫn đúng trong log 2024 dù sau đó đổi tên hay bị xóa tài khoản.
    actor_label: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(100), nullable=False)  # vd "doctor", "receptionist"

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # "booking.cancel"
    action_type: Mapped[AuditActionType] = mapped_column(
        Enum(AuditActionType, name="audit_action_type"), nullable=False
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "booking", "patient_record"
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Chỉ khác None khi resource liên quan trực tiếp 1 bệnh nhân cụ thể (PHI access).
    # Chỉ ID — KHÔNG lưu tên bệnh nhân ở đây (audit log không phải kho PHI thứ 2).
    target_patient_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Chỉ action_type=WRITE mới nên có giá trị. READ không cần old/new value.
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
