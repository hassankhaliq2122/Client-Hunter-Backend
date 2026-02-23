import sys
import os
import csv
import json
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure Logging for Production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Robust Path Handling
# This ensures that whether we are local or in a container, we find the core logic
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLIENT_HUNTER_DIR = os.path.join(BASE_DIR, "client_hunter")
sys.path.append(CLIENT_HUNTER_DIR)

logger.info(f"Production Startup: BASE_DIR resolved to {BASE_DIR}")
logger.info(f"Production Startup: CLIENT_HUNTER_DIR resolved to {CLIENT_HUNTER_DIR}")

try:
    import phase_a_discovery
    import phase_b_analyzer
    import phase_c_outreach
    logger.info("Core hunter modules imported successfully.")
except ImportError as e:
    logger.error(f"CRITICAL: Failed to import hunter modules. Check sys.path. Error: {e}")

app = FastAPI()

# Enable CORS for production (Explicitly allow Netlify)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://client-hunter.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Absolute File Paths for Lead Data
DISCOVERED_LEADS_CSV = os.path.join(CLIENT_HUNTER_DIR, "discovered_leads.csv")
ANALYZED_LEADS_CSV = os.path.join(CLIENT_HUNTER_DIR, "analyzed_leads.csv")
FINAL_OUTREACH_CSV = os.path.join(CLIENT_HUNTER_DIR, "final_outreach_list.csv")

class DiscoveryRequest(BaseModel):
    niche: str
    location: str

# Global Exception Handler to capture crashes and prevent 502/CORS issues
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"RUNTIME CRASH at {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal Server Error", "detail": str(exc)},
    )

@app.get("/")
def read_root():
    return {
        "message": "AI Client Hunter API is running",
        "status": "online",
        "base_dir": BASE_DIR
    }

@app.post("/run/phase-a")
async def run_phase_a(req: DiscoveryRequest):
    try:
        logger.info(f"Starting Phase A for niche: {req.niche} in {req.location}")
        leads = phase_a_discovery.search_businesses(req.niche, req.location, None)
        
        if not leads:
            return {"status": "success", "message": "No leads found", "count": 0}
        
        phase_a_discovery.save_to_csv(leads, DISCOVERED_LEADS_CSV)
        logger.info(f"Phase A completed. Found {len(leads)} leads.")
        return {"status": "success", "message": f"Found {len(leads)} leads", "count": len(leads)}
    except Exception as e:
        logger.error(f"Phase A Execution Error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.post("/run/phase-b")
async def run_phase_b():
    try:
        logger.info("Starting Phase B: Website Analysis")
        phase_b_analyzer.process_leads(DISCOVERED_LEADS_CSV, ANALYZED_LEADS_CSV)
        return {"status": "success", "message": "Website analysis completed"}
    except Exception as e:
        logger.error(f"Phase B Execution Error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.post("/run/phase-c")
async def run_phase_c():
    try:
        logger.info("Starting Phase C: Outreach Email Generation")
        phase_c_outreach.process_final_leads(ANALYZED_LEADS_CSV, FINAL_OUTREACH_CSV)
        return {"status": "success", "message": "Outreach email generation completed"}
    except Exception as e:
        logger.error(f"Phase C Execution Error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.get("/leads/{phase}")
async def get_leads(phase: str):
    file_map = {
        "a": DISCOVERED_LEADS_CSV,
        "b": ANALYZED_LEADS_CSV,
        "c": FINAL_OUTREACH_CSV
    }
    
    file_path = file_map.get(phase.lower())
    logger.info(f"GET leads request for phase '{phase}'. Resolved path: {file_path}")

    if not file_path:
        logger.warning(f"Invalid phase requested: {phase}")
        return []

    # Safe checking of file existence
    if not os.path.exists(file_path):
        logger.info(f"Lead file does not exist yet: {file_path}")
        return []
    
    leads = []
    try:
        # Robust CSV reading to prevent crashes
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            leads = [row for row in reader] # Materialize list immediately
            logger.info(f"Retrieved {len(leads)} leads from {os.path.basename(file_path)}")
    except Exception as e:
        logger.error(f"Failed to read CSV at {file_path}", exc_info=True)
        # Return empty list rather than 502 to maintain frontend stability
        return []
    
    return leads

if __name__ == "__main__":
    import uvicorn
    # Respect Railway's PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Uvicorn starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
