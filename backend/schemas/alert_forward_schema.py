"""
backend/schemas/alert_forward_schema.py
========================================
Pydantic v2 schemas for the Alert Forwarding feature.

This feature allows users to forward HIGH or CRITICAL risk thermal alerts
to concerned authorities as part of the prototype emergency-response workflow.

IMPORTANT:
  - Forwarding status is SUBMITTED_FOR_FORWARDING / FORWARDED_IN_SYSTEM
  - These statuses indicate the alert was submitted in the prototype system,
    NOT that it was actually delivered to an external government authority.
  - No real email/SMS/API integration exists in the prototype.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Authority definitions
# ---------------------------------------------------------------------------
class AuthorityRecord(BaseModel):
    id: str = Field(description="Unique authority identifier")
    name: str = Field(description="Display name of the authority")
    department: Optional[str] = Field(None, description="Department or ministry")
    contact_placeholder: Optional[str] = Field(
        None,
        description=(
            "Placeholder contact information for prototype demonstration. "
            "Do NOT use real personal contact details."
        ),
    )


# ---------------------------------------------------------------------------
# Forward request / response schemas
# ---------------------------------------------------------------------------
class AlertForwardRequest(BaseModel):
    authority_id: str = Field(description="Selected authority identifier")
    authority_name: str = Field(description="Human-readable authority name")
    authority_officer: Optional[str] = Field(
        None, description="Optional: name of the receiving officer"
    )
    authority_contact: Optional[str] = Field(
        None, description="Optional: contact email/phone (prototype placeholder only)"
    )
    message: str = Field(
        min_length=10,
        description="The forwarding message; must be non-empty and at least 10 characters",
    )
    include_report: bool = Field(
        default=True,
        description="Whether to include the structured incident report",
    )
    forwarded_by: Optional[str] = Field(
        None, description="Username or identifier of the operator forwarding the alert"
    )


class AlertForwardResponse(BaseModel):
    success: bool
    tracking_id: str = Field(
        description="Unique tracking ID for this forwarding record, e.g. FWD-TH004271-20260926-001"
    )
    event_id: str
    status: str = Field(
        description=(
            "SUBMITTED_FOR_FORWARDING — prototype only. "
            "Does NOT guarantee delivery to an actual government authority."
        )
    )
    authority: str
    timestamp: str = Field(description="ISO-8601 UTC timestamp of the forwarding record")
    message_preview: Optional[str] = Field(
        None, description="First 120 chars of the forwarding message"
    )


# ---------------------------------------------------------------------------
# Forwarding history record
# ---------------------------------------------------------------------------
class ForwardHistoryRecord(BaseModel):
    tracking_id: str
    event_id: str
    authority_id: str
    authority_name: str
    authority_officer: Optional[str] = None
    message: str
    include_report: bool
    forwarded_by: Optional[str] = None
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    status: str = Field(
        default="SUBMITTED_FOR_FORWARDING",
        description="Prototype forwarding status. NOT actual delivery confirmation.",
    )
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None


class ForwardHistoryResponse(BaseModel):
    event_id: str
    total: int
    records: List[ForwardHistoryRecord]
