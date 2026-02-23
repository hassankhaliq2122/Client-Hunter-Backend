import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import csv
import json

# Add the parent directory to sys.path to import from client_hunter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client_hunter")))

import phase_a_discovery
import phase_b_analyzer
import phase_c_outreach

app = FastAPI()

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLIENT_HUNTER_DIR = os.path.join(BASE_DIR, "client_hunter")
DISCOVERED_LEADS_CSV = os.path.join(CLIENT_HUNTER_DIR, "discovered_leads.csv")
ANALYZED_LEADS_CSV = os.path.join(CLIENT_HUNTER_DIR, "analyzed_leads.csv")
FINAL_OUTREACH_CSV = os.path.join(CLIENT_HUNTER_DIR, "final_outreach_list.csv")

class DiscoveryRequest(BaseModel):
    niche: str
    location: str

@app.get("/")
def read_root():
    return {"message": "AI Client Hunter API is running"}

@app.post("/run/phase-a")
def run_phase_a(req: DiscoveryRequest):
    try:
        leads = phase_a_discovery.search_businesses(req.niche, req.location, None)
        if not leads:
            return {"status": "success", "message": "No leads found", "count": 0}
        
        phase_a_discovery.save_to_csv(leads, DISCOVERED_LEADS_CSV)
        return {"status": "success", "message": f"Found {len(leads)} leads", "count": len(leads)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run/phase-b")
def run_phase_b():
    try:
        phase_b_analyzer.process_leads(DISCOVERED_LEADS_CSV, ANALYZED_LEADS_CSV)
        return {"status": "success", "message": "Website analysis completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run/phase-c")
def run_phase_c():
    try:
        phase_c_outreach.process_final_leads(ANALYZED_LEADS_CSV, FINAL_OUTREACH_CSV)
        return {"status": "success", "message": "Outreach email generation completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/leads/{phase}")
def get_leads(phase: str):
    file_map = {
        "a": DISCOVERED_LEADS_CSV,
        "b": ANALYZED_LEADS_CSV,
        "c": FINAL_OUTREACH_CSV
    }
    
    file_path = file_map.get(phase.lower())
    if not file_path or not os.path.exists(file_path):
        return []
    
    leads = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                leads.append(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return leads

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
