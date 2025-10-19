from copy import deepcopy
from typing import Dict, Any
import json, re


# === Parseur format texte -> dico en json === #
def parse_aba_plain(text: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = {
        "literals": [],
        "assumptions": [],
        "contraries": {},
        "rules": [],
        "preferences": ""
    }
    lits = set()
    def list_from_brackets(s):
        s = s.strip()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        return [x.strip() for x in s.split(",") if x.strip()]

    rule_pat = re.compile(r"^\s*\[[^\]]*\]\s*:\s*([A-Za-z0-9_]+)\s*<-\s*(.*)\s*$")
    contr_pat = re.compile(r"^C\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*:\s*([A-Za-z0-9_]+)\s*$", re.I)

    pref_str = None
    for ln in lines:
        if ln.startswith("L:"):
            inside = ln.split(":",1)[1].strip()
            for x in list_from_brackets(inside): lits.add(x)
            continue
        if ln.startswith("A:"):
            inside = ln.split(":",1)[1].strip()
            arr = list_from_brackets(inside)
            out["assumptions"] = arr
            for x in arr: lits.add(x)
            continue
        m = contr_pat.match(ln)
        if m:
            a, c = m.group(1), m.group(2)
            out["contraries"][a] = c
            lits.add(a); lits.add(c)
            continue
        m = rule_pat.match(ln)
        if m:
            head, body_txt = m.group(1), (m.group(2) or "").strip()
            body = [] if body_txt == "" else [x.strip() for x in body_txt.split(",") if x.strip()]
            out["rules"].append({"head": head, "body": body})
            lits.add(head); [lits.add(x) for x in body]
            continue
        if ln.upper().startswith("PREF"):
            pref_str = ln.split(":",1)[1].strip() if ":" in ln else ln.split(None,1)[1].strip()
            continue
        if "<-" in ln:  # ligne sans [rX]:
            head, body_txt = [p.strip() for p in ln.split("<-",1)]
            body = [] if body_txt == "" else [x.strip() for x in body_txt.split(",") if x.strip()]
            out["rules"].append({"head": head, "body": body})
            lits.add(head); [lits.add(x) for x in body]
            continue

    if not out["literals"]:
        out["literals"] = sorted(lits)
    out["preferences"] = pref_str or ""
    return out


def parse_any(payload: Dict[str, Any]):
    """
    Accepte :
      - {"input": "<texte ou JSON>", "__options": {...}}
      - {"literals": ..., "assumptions": ...} (déjà JSON)
    """
    opts = payload.get("__options", {}) or {}

    # Cas 1 : champ "input" = texte brut
    if "input" in payload and isinstance(payload["input"], str):
        raw = payload["input"].strip()
        if not raw:
            raise ValueError("Entrée vide.")
        # Si c’est du JSON
        if raw[0] in "{[":
            data = json.loads(raw)
        else:
            data = parse_aba_plain(raw)
        return data, opts

    # Cas 2 : on a déjà un JSON complet
    if {"literals","assumptions","contraries","rules"} <= set(payload.keys()):
        return payload, opts

    raise ValueError("Format d’entrée invalide (ni texte ni JSON complet).")

def parse_preferences(text):
    """
    Parse des préférences.
    Retourne un dict {assumption: rang} avec 0 = meilleur.
    """
    s = str(text).strip()
    if not s:
        return {}

    # Si ça utilise uniquement ">" (ex: a > b), et que a est MEILLEUR,
    # on doit le transformer en 'a < b' pour que le split par '<' fonctionne.
    # je ne sais pas pk mais ca fonctionne pas trop 
    if ">" in s and "<" not in s:
        # parts sera ['a', 'b'] pour 'a > b'.
        parts = [p.strip() for p in s.split(">") if p.strip()]
        # On ne fait AUCUNE inversion. On met juste le signe '<' pour que
        # la suite du code le traite dans l'ordre de préférence : meilleur < pire < ...
        s = " < ".join(parts) 

    # Maintenant on découpe par "<" (de meilleur vers moins bon)
    levels = []
    # On utilise replace('>', '<') pour le cas mixte (moins probable)
    for p in s.replace(">", "<").split("<"):
        p = p.strip()
        if not p:
            continue
        items = [x.strip() for x in p.replace(";", ",").split(",") if x.strip()]
        levels.append(items)

    pref = {}
    rank = 0
    for group in levels:
        for name in group:
            pref[name] = rank
        rank += 1
    return pref
