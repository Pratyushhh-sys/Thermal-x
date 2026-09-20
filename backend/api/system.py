"""
backend/api/system.py
========================
System administration API endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
import subprocess
import os
import logging
from pathlib import Path

router = APIRouter(prefix="/system", tags=["System"])
logger = logging.getLogger(__name__)

def run_firms_sync():
    """
    Background task to run the FIRMS download script.
    """
    try:
        project_root = Path(__file__).resolve().parents[2]
        script_path = project_root / "scripts" / "download_firms_data.py"
        
        logger.info(f"Starting FIRMS sync job: {script_path}")
        
        # Run the script
        result = subprocess.run(
            ["python", str(script_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"FIRMS sync job completed successfully.\n{result.stdout}")
        
        # Note: In a true production app, we would also trigger a reload of event_service and model inference here.
        # But this is a good starting point for the dashboard sync button.
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FIRMS sync job failed with exit code {e.returncode}.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
    except Exception as e:
        logger.error(f"Failed to run FIRMS sync job: {e}")

@router.post("/sync-firms")
def sync_firms_data(background_tasks: BackgroundTasks):
    """
    Triggers an asynchronous job to pull live data from NASA FIRMS.
    """
    background_tasks.add_task(run_firms_sync)
    return {"status": "accepted", "message": "NASA FIRMS synchronization started in the background."}
