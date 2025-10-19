from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.aba_core import ABA
from src.aba_transform import make_non_circular, make_atomic_sensitive
from src.aba_attacks import compute_attacks, compute_attacks_sets
from src.utils import parse_any


app = FastAPI()

# CORS permissif (pour dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod, restreins
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sert le front depuis ./web
app.mount("/web", StaticFiles(directory="web", html=False), name="web")

@app.get("/")
def index():
    return FileResponse("web/index.html")  # renomme si ton fichier a un autre nom

class RunOptions(BaseModel):
    use_prefs: bool = True
    non_circular: bool = False
    atomic: bool = False

class RunInput(BaseModel):
    data: dict
    options: RunOptions

@app.get("/health")
def health():
    return {"status": "ok"}


# @app.post("/api/aba/run")
# async def run(request: Request):
#     try:
#         payload = await request.json()
#         data, options = parse_any(payload)

#         do_non_circular = bool(options.get("do_non_circular", False))
#         do_atomic       = bool(options.get("do_atomic", False))
#         use_prefs       = bool(options.get("use_preferences", True))

#         aba = ABA.from_dict(data)
#         aba.validate()

#         if do_non_circular:
#             make_non_circular(aba)
#         if do_atomic:
#             make_atomic_sensitive(aba)

#         args = aba.derive_arguments()

#         # Attaques “par arguments” (pour le graphe) en respectant le switch prefs
#         atks = compute_attacks(aba, args, use_preferences=use_prefs)

#         # Attaques “par coalitions” (style prof) UNIQUEMENT si prefs cochée
#         if use_prefs:
#             atks_sets = compute_attacks_sets(aba, args)
#         else:
#             atks_sets = []

#         res = aba.export_results(args, atks)
#         res["attacks_sets"] = atks_sets
#         # renvoyer l'état des options au front
#         res["_options"] = {
#             "do_non_circular": do_non_circular,
#             "do_atomic": do_atomic,
#             "use_preferences": use_prefs,
#         }
#         return res

#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/aba/run")
async def run(request: Request):
    try:
        payload = await request.json()

        # Utilise TA fonction parse_any
        data, opts = parse_any(payload)

        do_non_circular = bool(opts.get("do_non_circular", False))
        do_atomic       = bool(opts.get("do_atomic", False))
        use_prefs       = bool(opts.get("use_preferences", True))

        # Construire ABA (data vient déjà de parse_any : soit depuis texte, soit JSON)
        aba = ABA.from_dict(data)
        aba.validate()

        if do_non_circular:
            make_non_circular(aba)
        if do_atomic:
            make_atomic_sensitive(aba)

        args = aba.derive_arguments()
        atks = compute_attacks(aba, args, use_preferences=use_prefs)
        atks_sets = compute_attacks_sets(aba, args) if use_prefs else []

        res = aba.export_results(args, atks)
        res["attacks_sets"] = atks_sets
        res["_options"] = {
            "do_non_circular": do_non_circular,
            "do_atomic": do_atomic,
            "use_preferences": use_prefs,
        }
        return res

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
