import os
import csv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Proper package imports
from client_hunter import phase_a_discovery
from client_hunter import phase_b_analyzer
from client_hunter import phase_c_outreach

app = FastAPI()

# ==============================
# CORS (Production Safe)
# ==============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://client-hunter.netlify.app",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# Paths Setup
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_HUNTER_DIR = os.path.join(BASE_DIR, "client_hunter")

# Ensure directory exists (prevents 502 crash)
os.makedirs(CLIENT_HUNTER_DIR, exist_ok=True)

DISCOVERED_LEADS_CSV = os.path.join(CLIENT_HUNTER_DIR, "discovered_leads.csv")
ANALYZED_LEADS_CSV = os.path.join(CLIENT_HUNTER_DIR, "analyzed_leads.csv")
FINAL_OUTREACH_CSV = os.path.join(CLIENT_HUNTER_DIR, "final_outreach_list.csv")


# ==============================
# Models
# ==============================
class DiscoveryRequest(BaseModel):
    niche: str
    location: str


# ==============================
# Health Check
# ==============================
@app.get("/")
def root():
    return {"message": "AI Client Hunter API is running"}


# ==============================
# Phase A
# ==============================
@app.post("/run/phase-a")
def run_phase_a(req: DiscoveryRequest):
    try:
        leads = phase_a_discovery.search_businesses(
            req.niche,
            req.location,
            None
        )

        if not leads:
            return {
                "status": "success",
                "message": "No leads found",
                "count": 0
            }

        phase_a_discovery.save_to_csv(leads, DISCOVERED_LEADS_CSV)

        return {
            "status": "success",
            "message": f"Found {len(leads)} leads",
            "count": len(leads)
        }

    except Exception as e:
        print("PHASE A ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Phase A failed")


# ==============================
# Phase B
# ==============================
@app.post("/run/phase-b")
def run_phase_b():
    try:
        if not os.path.isfile(DISCOVERED_LEADS_CSV):
            return {"status": "error", "message": "No discovered leads found"}

        phase_b_analyzer.process_leads(
            DISCOVERED_LEADS_CSV,
            ANALYZED_LEADS_CSV
        )

        return {
            "status": "success",
            "message": "Website analysis completed"
        }

    except Exception as e:
        print("PHASE B ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Phase B failed")


# ==============================
# Phase C
# ==============================
@app.post("/run/phase-c")
def run_phase_c():
    try:
        if not os.path.isfile(ANALYZED_LEADS_CSV):
            return {"status": "error", "message": "No analyzed leads found"}

        phase_c_outreach.process_final_leads(
            ANALYZED_LEADS_CSV,
            FINAL_OUTREACH_CSV
        )

        return {
            "status": "success",
            "message": "Outreach email generation completed"
        }

    except Exception as e:
        print("PHASE C ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Phase C failed")


# ==============================
# Get Leads (Safe — No 502)
# ==============================
@app.get("/leads/{phase}")
def get_leads(phase: str):

    file_map = {
        "a": DISCOVERED_LEADS_CSV,
        "b": ANALYZED_LEADS_CSV,
        "c": FINAL_OUTREACH_CSV
    }

    file_path = file_map.get(phase.lower())

    if not file_path:
        return []

    # If file doesn't exist, return empty safely
    if not os.path.isfile(file_path):
        return []

    leads = []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                leads.append(row)

        return leads

    except Exception as e:
        print("LEADS READ ERROR:", str(e))
        return []