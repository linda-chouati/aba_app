# src/aba_core.py
from itertools import product
from .utils import parse_preferences

class ABA:
    def __init__(self):
        # composant necessaire a le def du framework aba 
        self.literals = set()       # L : ensemble des littéraux
        self.assumptions = set()    # A : ensemble des hypothèses (assumptions)
        self.contraries = {}        # les contraires 
        self.rules = []           # R : règles de la forme avec head : body 
        self.preferences = {}       # préférences entre assumptions  pour aba+

    # ---------- parsing - check ----------

    def parse_from_json(self, data):
        """ va lire le cadre aba d un fichier json pour recup les données du framework """
        self.literals = set(data.get("literals", []))
        self.assumptions = set(data.get("assumptions", []))
        self.contraries = dict(data.get("contraries", {}))
        self.rules = list(data.get("rules", []))
        pref = data.get("preferences", {})
        if isinstance(pref, str):
            self.preferences = parse_preferences(pref)
        elif isinstance(pref, dict):
            self.preferences = dict(pref)
        else:
            self.preferences = {}

    def validate(self):
        """ juste pour vérifier que le framework est bien definit qu on a recup dans le fichier json"""
        if not self.literals:
            raise ValueError("literals manquant")
        if not self.assumptions:
            raise ValueError("assumptions manquant")

        for a in self.assumptions:
            if a not in self.literals:
                raise ValueError(f"assumption '{a}' pas dans L")

        for a, c in self.contraries.items():
            if a not in self.assumptions:
                raise ValueError(f"contrary pour '{a}' qui n'est pas une assumption")
            if c not in self.literals:
                raise ValueError(f"contrary '{c}' pas dans L")

        for r in self.rules:
            h = r.get("head")
            b = r.get("body", [])
            if h not in self.literals:
                raise ValueError(f"head invalide: {h}")
            for x in b:
                if x not in self.literals:
                    raise ValueError(f"body invalide: {x}")

    # ---------- arguments ----------

    def derive_arguments(self):
        """
        premiere etape essentielle trouver tous les arguments dérivable dans le cadre aba
        -> un argument est un couple (ensemble d asumption, conclusion)
        """
        supports = {l: set() for l in self.literals} # on garde pour chaque litteral, la liste des support donc des assumption qui le prouvent

        # une assumption permet de conclire elle meme : a |- a 
        for a in self.assumptions:
            supports[a].add(frozenset([a]))

        # poour les regles sans prémises, on conclut donc son head sans assumption 
        for r in self.rules:
            if not r.get("body", []):
                supports[r["head"]].add(frozenset())

        def keep_minimal(sets_):
            # juste pour etre sur qu on garde les support minimaux (pas de doublons)
            lst = list(sets_)
            out = []
            n = len(lst)
            for i in range(n):
                s = lst[i]
                ok = True
                for j in range(n):
                    if i == j:
                        continue
                    if lst[j] < s: # si un support plus petit existe on peut supp s 
                        ok = False
                        break
                if ok:
                    out.append(s)
            return set(out)

        # on apllique la fermeture par application de reles -> proprogation jusqu a stabilité 
        changed = True
        while changed:
            changed = False
            for r in self.rules:
                head = r["head"]
                body = r.get("body", [])
                if not body:
                    continue

                # on ne peut pas appliquer la regles si toutes le prémises sont deja dérivables 
                all_ok = True
                for b in body:
                    if len(supports[b]) == 0:
                        all_ok = False
                        break
                if not all_ok:
                    continue

                # on constuit donc des nouveaux support pour le head
                pools = []
                for b in body:
                    pools.append(list(supports[b]))
                for combo in product(*pools):
                    uni = frozenset()
                    for s in combo:
                        uni = uni.union(s)
                    if uni not in supports[head]:
                        supports[head].add(uni)
                        changed = True

                # on garde uniquement les support munimaux 
                new_min = keep_minimal(supports[head])
                if new_min != supports[head]:
                    supports[head] = new_min
                    changed = True

        # on convertir ca en liste d arguments 
        args = []
        idx = 0
        for concl, sets_ass in supports.items():
            for S in sets_ass:
                args.append({"id": idx, "assumptions": S, "conclusion": concl})
                idx += 1
        return args

    # ---------- export du resultats ----------

    def export_results(self, args, atks):
        """on stocke ses resultats en json (arguments + attaques)"""
        out_args = []
        for a in args:
            out_args.append({
                "id": a["id"],
                "conclusion": a["conclusion"],
                "assumptions": sorted(list(a["assumptions"]))
            })
        return {
            "literals": sorted(self.literals),
            "assumptions": sorted(self.assumptions),
            "contraries": dict(self.contraries),
            "rules": self.rules,
            "preferences": self.preferences,
            "arguments": out_args,
            "attacks": atks
        }
    
