import json
from itertools import product

# === Fonctions utilitaires ===

def parse_preferences(pref_text):
    """
    Parse le champ de préférences PREF: "a,b > c > d"
    et renvoie un dict {hypothese: rang}, avec :
      - rang 0 = le plus préféré
      - rang 1, 2, ... = moins préféré
    Exemple : "a,b > c > d" -> a:0, b:0, c:1, d:2
    """
    levels = [level.strip() for level in pref_text.split(">") if level.strip()]
    preferences = {}
    for level, group in enumerate(levels):
        assumptions = [a.strip() for a in group.split(",") if a.strip()]
        for assumption in assumptions:
            preferences[assumption] = level
    return preferences


# === Classe principale ABA avec la logique métier ===

class ABA:
    def __init__(self):
        self.literals = set()      # L'ensemble des littéraux (L)
        self.assumptions = set()   # L'ensemble des hypothèses (A)
        self.contraries = {}       # dict hypothèse -> son contraire (C)
        self.rules = []            # liste des règles: {"head": str, "body": [str, ...]}
        self.preferences = {}      # dict hypothèse -> rang (0 = meilleur)

    # ------------------ Parsing & validation ------------------

    def parse_from_json(self, json_input):
        """
        Charge la structure ABA depuis un dict (JSON déjà parsé).
        """
        self.literals = set(json_input.get('literals', []))
        self.assumptions = set(json_input.get('assumptions', []))
        self.contraries = dict(json_input.get('contraries', {}))
        self.rules = list(json_input.get('rules', []))

        pref_data = json_input.get('preferences', {})
        if isinstance(pref_data, dict):
            self.preferences = dict(pref_data)
        elif isinstance(pref_data, str):
            self.preferences = parse_preferences(pref_data)
        else:
            self.preferences = {}

    def validate(self):
        if not self.literals:
            raise ValueError("Aucun littéral (literals) défini.")
        if not self.assumptions:
            raise ValueError("Aucune hypothèse (assumptions) définie.")

        # Hypothèses doivent être dans L
        for a in self.assumptions:
            if a not in self.literals:
                raise ValueError(f"Hypothèse '{a}' absente des littéraux.")

        # Contraires bien formés
        for a, c in self.contraries.items():
            if a not in self.assumptions:
                raise ValueError(f"Contrary défini pour '{a}', qui n'est pas une hypothèse.")
            if c not in self.literals:
                raise ValueError(f"Contrary '{c}' pour '{a}' absent des littéraux.")

        # Règles bien formées
        for rule in self.rules:
            head = rule.get('head')
            body = rule.get('body', [])
            if head not in self.literals:
                print(f"Erreur : tête de règle '{head}' invalide.")
            for elem in body:
                if elem not in self.literals:
                    print(f"Erreur : élément '{elem}' dans le corps de règle invalide.")

        print("grammaire vérifier")

    # ------------------ Génération d'arguments ------------------

    def derive_arguments(self):
        """
        Génère tous les arguments possibles du framework ABA.
        Retourne une liste d'arguments:
          {"assumptions": frozenset({...}), "conclusion": <littéral>}
        Règles :
          - Toute hypothèse a supporte elle-même a  : {a} |- a
          - Une règle factuelle (body = []) supporte head sans hypothèse : {} |- head
          - Si toutes les prémisses d'une règle ont des supports, head est supporté
            par l'union de ces supports (en gardant seulement les ensembles MINIMAUX).
        """
        # pour chaque littéral, ensemble des supports (frozenset d'hypothèses)
        supports = {literal: set() for literal in self.literals}

        # 1) hypothèse -> elle-même
        for hypothesis in self.assumptions:
            supports[hypothesis].add(frozenset({hypothesis}))

        # 2) faits -> head sans hypothèses
        for rule in self.rules:
            if not rule.get("body", []):
                supports[rule["head"]].add(frozenset())

        def minimal_sets(sets_of_sets):
            """
            Ne garde que les ensembles minimaux (aucun autre n'est strictement inclus).
            """
            sets_list = list(sets_of_sets)
            minimal = []
            for i, s in enumerate(sets_list):
                if not any(other < s for j, other in enumerate(sets_list) if i != j):
                    minimal.append(s)
            return set(minimal)

        # 3) propagation jusqu'à stabilisation
        changed = True
        while changed:
            changed = False
            for rule in self.rules:
                head = rule["head"]
                body = rule.get("body", [])
                if not body:
                    continue  # déjà traité

                # toutes les prémisses doivent avoir au moins un support
                if all(supports.get(b) for b in body):
                    # produit cartésien des supports des prémisses
                    for combo in product(*(supports[b] for b in body)):
                        union_support = frozenset().union(*combo)
                        if union_support not in supports[head]:
                            supports[head].add(union_support)
                            changed = True

                    # minimalisation pour head
                    new_min = minimal_sets(supports[head])
                    if new_min != supports[head]:
                        supports[head] = new_min
                        changed = True

        # construire la liste d'arguments
        arguments = []
        for conclusion, sets_ass in supports.items():
            for ass_set in sets_ass:
                arguments.append({"assumptions": ass_set, "conclusion": conclusion})
        return arguments

    # ------------------ Attaques avec préférences (ABA+) ------------------

    def compute_attacks(self, arguments):
        """
        Conventions de préférences :
          - self.preferences mappe chaque hypothèse vers un RANG (0 = meilleur, 1 = moins bon, etc.)
        Définition de l'attaque :
          - A (i) attaque B (j) ssi concl(A) == C(b) pour une hypothèse b ∈ supp(B).
          - Si ∃ a ∈ supp(A) avec rank(a) > rank(b) (donc a moins préférée que b),
            ALORS l'attaque est renversée (B -> A) de type 'reverse'.
          - Sinon l'attaque est normale (A -> B) de type 'normal'.
        Retour :
          liste de dicts: {"attacker": i, "target": j, "kind": "normal"/"reverse", "witness": b}
        """
        def rank(x):
            # hypothèse non mentionnée => on lui donne un rang très mauvais
            return self.preferences.get(x, 10**6)

        # s'assurer qu'on a un id pour chaque argument
        for idx, a in enumerate(arguments):
            a.setdefault("id", idx)

        attacks = []
        seen = set()  # pour éviter les doublons (attacker, target, kind, witness)

        for A in arguments:
            i = A["id"]
            conclA = A["conclusion"]
            for B in arguments:
                j = B["id"]
                if i == j:
                    continue
                for b in B["assumptions"]:
                    if self.contraries.get(b) == conclA:
                        # test de préférence sur les HYPOTHESES de A (pas sur sa conclusion)
                        reverse = any(rank(a) > rank(b) for a in A["assumptions"])
                        if reverse:
                            key = (j, i, "reverse", b)
                            if key not in seen:
                                seen.add(key)
                                attacks.append({"attacker": j, "target": i, "kind": "reverse", "witness": b})
                        else:
                            key = (i, j, "normal", b)
                            if key not in seen:
                                seen.add(key)
                                attacks.append({"attacker": i, "target": j, "kind": "normal", "witness": b})
        return attacks

    # ------------------ Détection de cycles ------------------

    def has_cycles(self):
        """
        Vérifie si le graphe des règles contient un cycle.
        Retourne True s'il y a un cycle, False sinon.
        """
        # graphe d'adjacence : body_lit -> head
        graph = {lit: [] for lit in self.literals}
        for rule in self.rules:
            head = rule['head']
            for body_lit in rule.get('body', []):
                graph[body_lit].append(head)

        visited = set()
        rec_stack = set()

        def dfs(node):
            if node in rec_stack:
                return True  # cycle détecté
            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if dfs(neighbor):
                    return True
            rec_stack.remove(node)
            return False

        for literal in self.literals:
            if literal not in visited:
                if dfs(literal):
                    return True
        return False

    # ------------------ Export pour API ------------------

    def export_results(self, arguments, attacks):
        # s'assurer que chaque argument a un id
        for i, a in enumerate(arguments):
            a.setdefault("id", i)
        return {
            "literals": sorted(self.literals),
            "assumptions": sorted(self.assumptions),
            "contraries": dict(self.contraries),
            "rules": self.rules,
            "preferences": self.preferences,
            "arguments": [
                {"id": a["id"], "conclusion": a["conclusion"], "assumptions": sorted(list(a["assumptions"]))}
                for a in arguments
            ],
            "attacks": attacks
        }


# ------------------ Test console ------------------

def mainTest():
    with open('exemple.json', 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    aba = ABA()
    aba.parse_from_json(json_data)

    print("Littéraux :", aba.literals)
    print("Hypothèses :", aba.assumptions)
    print("Contraires :", aba.contraries)
    print("Règles :", aba.rules)
    print("Préférences :", aba.preferences)

    aba.validate()

    arguments = aba.derive_arguments()
    print("\nArguments générés :")
    for i, arg in enumerate(arguments):
        print(f"A{i}: {arg['conclusion']} <= {sorted(list(arg['assumptions']))}")

    attacks = aba.compute_attacks(arguments)
    print("\nAttaques détectées :")
    for atk in attacks[:15]:
        print(f"{atk['kind'].upper()}: A{atk['attacker']} -> A{atk['target']} (vise '{atk['witness']}')")

    if aba.has_cycles():
        print("Erreur : le framework ABA contient un cycle !")
    else:
        print("Framework ABA sans cycle détecté.")


if __name__ == "__main__":
    mainTest()
