"""
backend/api/imagery.py
========================
API endpoints for fetching satellite imagery from Sentinel Hub.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from backend.services.event_service import event_service
from backend.services.imagery_service import imagery_service

router = APIRouter(prefix="/imagery", tags=["Imagery"])

@router.get("/{event_id}")
def get_event_imagery(event_id: str):
    """
    Fetches the true color satellite imagery for the given event ID.
    """
    try:
        event = event_service.get_event_row(event_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Event not found")
        
    lat = float(event.get("latitude", 0))
    lng = float(event.get("longitude", 0))
    acq_date = event.get("acq_date")
    
    if lat == 0 and lng == 0:
        raise HTTPException(status_code=400, detail="Invalid event coordinates")
        
    image_bytes = imagery_service.fetch_true_color_image(
        lat=lat,
        lng=lng,
        radius_km=2.0,
        acq_date=acq_date,
        event_id=event_id,
    )
    
    if not image_bytes:
        # Graceful fallback: return the high-resolution fallback thumbnail if available
        from pathlib import Path
        fallback_path = Path(__file__).resolve().parents[2] / "frontend" / "public" / "assets" / "selected_event_th1024.png"
        if fallback_path.exists():
            return Response(content=fallback_path.read_bytes(), media_type="image/png")
        raise HTTPException(status_code=500, detail="Failed to fetch imagery from Sentinel Hub")
        
    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
