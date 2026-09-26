"""
backend/api/imagery.py
========================
API endpoints for fetching satellite imagery from Sentinel Hub / CDSE.

GET /api/imagery/{event_id}           -- Sentinel-2 L2A true-color optical image (bytes)
GET /api/imagery/{event_id}/thermal   -- Sentinel-3 SLSTR S8 TIR thermal image (bytes)
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from backend.services.event_service import event_service
from backend.services.imagery_service import imagery_service
from backend.services.thermal_imagery_service import thermal_imagery_service

router = APIRouter(prefix="/imagery", tags=["Imagery"])


@router.api_route("/{event_id}", methods=["GET", "HEAD"])
def get_event_imagery(event_id: str, request: Request):
    """
    Fetches the Sentinel-2 L2A true-color (optical) image for the given event ID.
    Bands: B04 (R), B03 (G), B02 (B) — enhanced 2.5x gain.
    Resolution: 10 m. Source: Copernicus Data Space / Sentinel Hub.
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


@router.api_route("/{event_id}/thermal", methods=["GET", "HEAD"])
def get_event_thermal_imagery(event_id: str, request: Request):
    """
    Fetches the Sentinel-3 SLSTR thermal infrared image for the given event ID.

    Band: S8 (10.85 um - Thermal Infrared)
    Resolution: ~1 km at nadir
    Color ramp: IRON heatmap (black->red->orange->yellow->white = cold->hot)
    Temporal window: +-24 hours around event acquisition time
    Source: Copernicus Data Space Ecosystem (CDSE)

    Returns:
      200 + JPEG bytes if thermal scene is available
      404 if event not found
      204 No Content if no thermal scene available (caller should use metadata endpoint)
    """
    try:
        event = event_service.get_event_row(event_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Event not found")

    lat = float(event.get("latitude", 0))
    lng = float(event.get("longitude", 0))
    acq_date = event.get("acq_date")
    acq_time = event.get("acq_time")

    if lat == 0 and lng == 0:
        raise HTTPException(status_code=400, detail="Invalid event coordinates")

    result = thermal_imagery_service.fetch_thermal_image(
        lat=lat,
        lng=lng,
        acq_date=str(acq_date) if acq_date else None,
        acq_time_hhmm=str(acq_time) if acq_time else None,
        event_id=event_id,
        radius_km=5.0,
    )

    if not result["available"] or not result["image_bytes"]:
        # Return 204 so the frontend knows thermal is unavailable
        # (instead of breaking with 500)
        return Response(status_code=204)

    if request.method == "HEAD":
        return Response(
            status_code=200,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-Thermal-Source": result.get("source", "Sentinel-3 SLSTR"),
                "X-Thermal-Acquisition": result.get("acquisition_time", ""),
                "X-Thermal-Delta-Minutes": str(result.get("time_delta_minutes", "")),
            },
        )

    return Response(
        content=result["image_bytes"],
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Thermal-Source": result.get("source", "Sentinel-3 SLSTR"),
            "X-Thermal-Acquisition": result.get("acquisition_time", ""),
            "X-Thermal-Delta-Minutes": str(result.get("time_delta_minutes", "")),
        },
    )
