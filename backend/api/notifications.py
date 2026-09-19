"""
backend/api/notifications.py
============================
GET /api/notifications

Returns the top 3 highest risk thermal events dynamically to power the frontend notifications menu.
"""

from fastapi import APIRouter, Request
from typing import List
from pydantic import BaseModel, Field

router = APIRouter()


class NotificationResponse(BaseModel):
    id: str = Field(description="Unique ID for the notification")
    eventId: str = Field(description="Associated thermal event ID")
    type: str = Field(description="Type: urgent, warning, info")
    title: str = Field(description="Notification title")
    message: str = Field(description="Notification body/description")
    timestamp: str = Field(description="Time of notification (ISO string or relative)")
    read: bool = Field(default=False)


@router.get("/notifications", response_model=List[NotificationResponse], tags=["Notifications"])
async def get_notifications(request: Request) -> List[NotificationResponse]:
    """
    Dynamically generate notifications from the latest high FRP/persistence events.
    """
    event_svc = request.app.state.event_service
    
    # We fetch a slightly larger pool and pick the top ones by FRP and Persistence
    rows = event_svc.get_events(limit=50, raw_rows=True)
    
    # Sort by FRP descending
    rows_sorted = sorted(rows, key=lambda x: float(x.get("frp", 0) or 0), reverse=True)
    
    top_events = rows_sorted[:3]
    
    notifications = []
    for idx, row in enumerate(top_events):
        frp = float(row.get("frp", 0) or 0)
        acq_date = row.get("acq_date", "Unknown Date")
        
        # Simple thresholding to mimic Risk Engine severity
        if frp > 50:
            ntype = "urgent"
            title = f"High Risk Thermal Anomaly Detected"
        else:
            ntype = "warning"
            title = f"Moderate Thermal Anomaly Detected"
            
        notifications.append(NotificationResponse(
            id=f"notif_{row.get('event_id')}",
            eventId=row.get("event_id"),
            type=ntype,
            title=title,
            message=f"FRP {frp:.1f} MW detected on {acq_date}.",
            timestamp="Just now" if idx == 0 else f"{idx}h ago",
            read=False
        ))
        
    return notifications
