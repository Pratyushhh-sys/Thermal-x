"""
backend/services/alert_forward_service.py
==========================================
In-memory service for the Alert Forwarding feature.

Design decisions:
  - In-memory storage (dict keyed by event_id → list of ForwardHistoryRecord)
    is appropriate for the SIH prototype. No database dependency introduced.
  - Forwarding status is always SUBMITTED_FOR_FORWARDING — this is a prototype.
  - Tracking IDs are generated deterministically from event_id + timestamp + counter.
  - Audit records capture every field for compliance traceability.
  - Eligible tiers: HIGH and CRITICAL (score >= 70 in current risk_service thresholds).

Extending to production:
  - Replace the in-memory store with a database (PostgreSQL / MongoDB).
  - Add a real notification adapter (email/SMS/government API).
  - Change status to FORWARDED or DELIVERED after confirmed dispatch.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.schemas.alert_forward_schema import (
    AlertForwardRequest,
    AlertForwardResponse,
    ForwardHistoryRecord,
    ForwardHistoryResponse,
    AuthorityRecord,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable mock authority list (prototype — no real contacts)
# ---------------------------------------------------------------------------
MOCK_AUTHORITIES: List[AuthorityRecord] = [
    AuthorityRecord(
        id="DIST_ADMIN",
        name="District Administration",
        department="Revenue & Disaster Management",
        contact_placeholder="district.collector@example.gov.in [PROTOTYPE]",
    ),
    AuthorityRecord(
        id="SPCB",
        name="State Pollution Control Board",
        department="Environment & Climate",
        contact_placeholder="spcb.duty@example.gov.in [PROTOTYPE]",
    ),
    AuthorityRecord(
        id="SDMA",
        name="Disaster Management Authority",
        department="State Disaster Management Authority",
        contact_placeholder="sdma.ops@example.gov.in [PROTOTYPE]",
    ),
    AuthorityRecord(
        id="FIRE_SVC",
        name="Fire & Emergency Services",
        department="Home Department",
        contact_placeholder="fire.control@example.gov.in [PROTOTYPE]",
    ),
    AuthorityRecord(
        id="FOREST_DEPT",
        name="Forest Department",
        department="Environment & Forest",
        contact_placeholder="forest.division@example.gov.in [PROTOTYPE]",
    ),
    AuthorityRecord(
        id="ISA",
        name="Industrial Safety Authority",
        department="Labour & Employment / Factories Inspectorate",
        contact_placeholder="factory.inspector@example.gov.in [PROTOTYPE]",
    ),
    AuthorityRecord(
        id="EMA",
        name="Environmental Monitoring Authority",
        department="Ministry of Environment, Forest & Climate Change",
        contact_placeholder="ema.monitor@example.gov.in [PROTOTYPE]",
    ),
    AuthorityRecord(
        id="OTHER",
        name="Other",
        department=None,
        contact_placeholder=None,
    ),
]

# ---------------------------------------------------------------------------
# In-memory audit store: { event_id: [ForwardHistoryRecord, ...] }
# ---------------------------------------------------------------------------
_forward_history: Dict[str, List[ForwardHistoryRecord]] = {}

# Per-event forwarding counter for tracking ID suffix
_event_forward_counter: Dict[str, int] = {}


# ---------------------------------------------------------------------------
# Eligible risk tiers for forwarding
# ---------------------------------------------------------------------------
ELIGIBLE_TIERS = frozenset({"HIGH", "CRITICAL"})


def get_authorities() -> List[AuthorityRecord]:
    """Return the configurable authority list."""
    return MOCK_AUTHORITIES


def _generate_tracking_id(event_id: str, now: datetime, counter: int) -> str:
    """
    Generate a human-readable tracking ID.
    Format: FWD-<EVENTID>-<YYYYMMDD>-<NNN>
    """
    date_str = now.strftime("%Y%m%d")
    # Strip any non-alphanumeric characters from event_id for safe embedding
    safe_eid = "".join(c for c in event_id if c.isalnum() or c == "-").upper()
    return f"FWD-{safe_eid}-{date_str}-{counter:03d}"


def forward_alert(
    event_id: str,
    risk_tier: str,
    risk_score: float,
    request: AlertForwardRequest,
) -> AlertForwardResponse:
    """
    Record a forwarding action for a HIGH/CRITICAL risk event.

    Parameters
    ----------
    event_id   : The thermal event ID (already verified by the router)
    risk_tier  : The risk tier from the event intelligence pipeline
    risk_score : The composite risk score
    request    : The validated forward request payload

    Returns
    -------
    AlertForwardResponse with tracking ID and prototype status
    """
    now = datetime.now(timezone.utc)

    # Increment per-event counter
    _event_forward_counter[event_id] = _event_forward_counter.get(event_id, 0) + 1
    counter = _event_forward_counter[event_id]

    tracking_id = _generate_tracking_id(event_id, now, counter)
    timestamp_str = now.isoformat()

    record = ForwardHistoryRecord(
        tracking_id=tracking_id,
        event_id=event_id,
        authority_id=request.authority_id,
        authority_name=request.authority_name,
        authority_officer=request.authority_officer,
        message=request.message,
        include_report=request.include_report,
        forwarded_by=request.forwarded_by,
        timestamp=timestamp_str,
        status="SUBMITTED_FOR_FORWARDING",
        risk_level=risk_tier,
        risk_score=risk_score,
    )

    if event_id not in _forward_history:
        _forward_history[event_id] = []
    _forward_history[event_id].append(record)

    logger.info(
        "AUDIT | forward_alert | event=%s | authority=%s | tracking=%s | risk=%s/%.1f | by=%s",
        event_id,
        request.authority_name,
        tracking_id,
        risk_tier,
        risk_score,
        request.forwarded_by or "unknown",
    )

    return AlertForwardResponse(
        success=True,
        tracking_id=tracking_id,
        event_id=event_id,
        status="SUBMITTED_FOR_FORWARDING",
        authority=request.authority_name,
        timestamp=timestamp_str,
        message_preview=request.message[:120] if request.message else None,
    )


def get_forward_history(event_id: str) -> ForwardHistoryResponse:
    """Return all forwarding records for a given event."""
    records = _forward_history.get(event_id, [])
    return ForwardHistoryResponse(
        event_id=event_id,
        total=len(records),
        records=records,
    )


def has_been_forwarded(event_id: str) -> bool:
    """Return True if this event has at least one forwarding record."""
    return bool(_forward_history.get(event_id))
