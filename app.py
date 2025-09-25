from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any
from aba import ABA

app = FastAPI(title="ABA Generator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# pour les fichiers statics
app.mount("/web", StaticFiles(directory="web"), name="web")

# pour avoir l interface direct à la racine 
@app.get("/")
def serve_index():
    return FileResponse("web/index.html")

# l api 
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/run")
def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        aba = ABA()
        aba.parse_from_json(payload)
        aba.validate()
        args = aba.derive_arguments()
        atks = aba.compute_attacks(args)  
        return aba.export_results(args, atks)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
