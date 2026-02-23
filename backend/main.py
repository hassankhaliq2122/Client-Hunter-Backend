import os
import csv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Proper package imports (NO sys.path hacks)
from client_hunter import phase_a_discovery
from client_hunter import phase_b_analyzer
from client_hunter import phase_c_outreach

app = FastAPI()

# ===============================
# CORS Configuration (Production)
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://client-hunter.netlify.app",
        "http://localhost:5173",  # local dev (Vite)
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# File Paths
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_HUNTER_DIR = os.path.join(BASE_DIR, "client_hunter")

DISCOVERED_LEADS_CSV = os.path.join(CLIENT_HUNTER_DIR, "discovered_leads.csv")
ANALYZED_LEADS_CSV = os.path.join(CLIENT_HUNTER_DIR, "analyzed_leads.csv")
FINAL_OUTREACH_CSV = os.path.join(CLIENT_HUNTER_DIR, "final_outreach_list.csv")


# ===============================
# Request Models
# ===============================
class DiscoveryRequest(BaseModel):
    niche: str
    location: str


# ===============================
# Routes
# ===============================
@app.get("/")
def root():
    return {"message": "AI Client Hunter API is running"}


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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run/phase-b")
def run_phase_b():
    try:
        phase_b_analyzer.process_leads(
            DISCOVERED_LEADS_CSV,
            ANALYZED_LEADS_CSV
        )

        return {
            "status": "success",
            "message": "Website analysis completed"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run/phase-c")
def run_phase_c():
    try:
        phase_c_outreach.process_final_leads(
            ANALYZED_LEADS_CSV,
            FINAL_OUTREACH_CSV
        )

        return {
            "status": "success",
            "message": "Outreach email generation completed"
        }

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

    try:
        leads = []
        with open(file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                leads.append(row)

        return leads

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))