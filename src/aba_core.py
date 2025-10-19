from itertools import product
from src.utils import parse_preferences

class ABA:
    """
    Cadre ABA minimal :
      - literals : ensemble de littéraux
      - assumptions : sous-ensemble de literals
      - contraries : dict assumption -> literal
      - rules : liste de dict {"head": str, "body": [str,...]}
      - preferences : dict optionnel assumption -> rang (0 = meilleur)
    """

    def __init__(self):
        self.literals = set()
        self.assumptions = set()
        self.contraries = {}
        self.rules = []
        self.preferences = {}

    # ---------- construction ----------

    @classmethod
    def from_dict(cls, data):
        obj = cls()
        obj.literals = set(data.get("literals", []))
        obj.assumptions = set(data.get("assumptions", []))
        obj.contraries = dict(data.get("contraries", {}))
        obj.rules = list(data.get("rules", []))

        pref = data.get("preferences", {})
        if isinstance(pref, str):
            obj.preferences = parse_preferences(pref)
        elif isinstance(pref, dict):
            obj.preferences = dict(pref)
        else:
            obj.preferences = {}
        obj.validate()
        return obj

    def validate(self):
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

    # ---------- génération d'arguments ----------

    def derive_arguments(self):
        """
        Génère tous les arguments minimaux possibles.
        Un argument = {"id": int, "assumptions": frozenset(...), "conclusion": literal}
        """
        supports = {l: set() for l in self.literals}

        # une assumption prouve elle-même
        for a in self.assumptions:
            supports[a].add(frozenset([a]))

        # règles sans prémisses
        for r in self.rules:
            if not r.get("body", []):
                supports[r["head"]].add(frozenset())

        # fermeture par règles jusqu'à stabilité
        def minimalize(sets_):
            lst = list(sets_)
            keep = []
            n = len(lst)
            for i in range(n):
                s = lst[i]
                ok = True
                for j in range(n):
                    if i == j: 
                        continue
                    if lst[j] < s:  # strict subset
                        ok = False
                        break
                if ok:
                    keep.append(s)
            return set(keep)

        changed = True
        while changed:
            changed = False
            for r in self.rules:
                head = r["head"]
                body = r.get("body", [])
                if not body:
                    continue
                # il faut que toutes les prémisses soient déjà prouvables
                for b in body:
                    if len(supports[b]) == 0:
                        break
                else:
                    # composer les supports
                    pools = [list(supports[b]) for b in body]
                    for combo in product(*pools):
                        acc = frozenset().union(*combo)
                        if acc not in supports[head]:
                            supports[head].add(acc)
                            changed = True
                    # garder les supports minimaux
                    new_min = minimalize(supports[head])
                    if new_min != supports[head]:
                        supports[head] = new_min
                        changed = True

        # conversion en liste
        args = []
        k = 0
        for concl, Sset in supports.items():
            for S in Sset:
                args.append({"id": k, "assumptions": S, "conclusion": concl})
                k += 1
        return args

    # ---------- export ----------

    def export_results(self, args, attacks):
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
            "attacks": attacks
        }
