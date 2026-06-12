"""Audit logging for compliance."""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    QUERY = "query"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACCESS_DENIED = "access_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class AuditEvent(BaseModel):
    timestamp: str
    event_type: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    resource: str
    action: str
    success: bool
    ip_address: Optional[str] = None
    metadata: Dict[str, Any] = {}


class AuditLogger:
    def __init__(self):
        self.events: list[AuditEvent] = []

    def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        resource: str,
        action: str,
        success: bool = True,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ):
        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type.value,
            user_id=user_id,
            tenant_id=tenant_id,
            resource=resource,
            action=action,
            success=success,
            ip_address=ip_address,
            metadata=metadata or {},
        )
        self.events.append(event)
        logger.info(f"Audit: {event.model_dump_json()}")

    def login(self, user_id: str, tenant_id: Optional[str] = None, ip: str = None):
        self.log(AuditEventType.LOGIN, user_id, "auth", "login", True, tenant_id, ip)

    def access_denied(self, user_id: str, resource: str, ip: str = None):
        self.log(AuditEventType.ACCESS_DENIED, user_id, resource, "access", False, ip=ip)

    def query(self, user_id: str, query: str, tenant_id: Optional[str] = None):
        self.log(
            AuditEventType.QUERY,
            user_id,
            "query",
            "execute",
            True,
            tenant_id,
            metadata={"query": query},
        )


_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
