from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any

from src.aba_core import ABA
from src.aba_transform import make_non_circular, make_atomic_sensitive
from src.aba_attacks import compute_attacks

app = FastAPI(title="ABA Generator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# sert les fichiers statiques depuis /web
app.mount("/web", StaticFiles(directory="web"), name="web")

# page d'accueil 
@app.get("/")
def serve_index():
    return FileResponse("web/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

# === ENDPOINT -> la pi 
@app.post("/api/aba/run")
def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attend un JSON du cadre ABA (et des options si y'en a) et renvoie:
      - literals, assumptions, contraries, rules, preferences
      - arguments: 
      - attacks:   
    """
    try:
        body = dict(payload)  
        options = body.pop("__options", {}) or {}
        do_non_circular = bool(options.get("do_non_circular", False))
        do_atomic       = bool(options.get("do_atomic", False))
        use_prefs       = bool(options.get("use_preferences", True))

        aba = ABA()
        aba.parse_from_json(body)
        aba.validate()

        if do_non_circular:
            make_non_circular(aba)
        if do_atomic:
            make_atomic_sensitive(aba)

        args = aba.derive_arguments()
        atks = compute_attacks(aba, args, use_preferences=use_prefs)

        return aba.export_results(args, atks)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
