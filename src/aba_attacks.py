
def _is_strictly_less(x, y, prefs):
    """
    True si x est STRICTEMENT moins préféré que y (rang(x) > rang(y)).
    Si l'un n'a pas de rang => incomparables => False.
    """
    rx = prefs.get(x, None)
    ry = prefs.get(y, None)
    if rx is None or ry is None:
        return False
    return rx > ry  # rang 0 = meilleur

def compute_attacks(aba, args, use_preferences=False):
    """
    Calcule les attaques argument -> argument.
    - Sans préférences : A -> B si concl(A) = contrary(b) pour un b ∈ Supp(B).
    - Avec préférences (simple et standard en ABA+) :
        * Normal: A -> B si, pour ce b, aucun a ∈ Supp(A) n'est STRICTEMENT moins préféré que b.
        * Reverse: sinon (B -> A).
      On agrège par paire (A,B): priorité au 'normal', sinon 'reverse' (au plus 1 arête par paire).
    """
    pair = {}  # (i,j) -> {"normal": set(witness), "reverse": set(witness)}

    def reg(kind, i, j, w):
        entry = pair.setdefault((i, j), {"normal": set(), "reverse": set()})
        entry[kind].add(w)

    for A in args:
        i = A["id"]; conclA = A["conclusion"]; suppA = A["assumptions"]
        for B in args:
            j = B["id"]; suppB = B["assumptions"]
            for b in suppB:
                if aba.contraries.get(b) != conclA:
                    continue
                if not use_preferences:
                    reg("normal", i, j, b)
                else:
                    any_less = any(_is_strictly_less(a, b, aba.preferences) for a in suppA)
                    if any_less:
                        reg("reverse", j, i, b)  # inversion
                    else:
                        reg("normal", i, j, b)

    attacks = []
    seen = set()
    for (i, j), kinds in pair.items():
        if kinds["normal"]:
            w = sorted(kinds["normal"])[0]
            key = (i, j, "normal", w)
            if key not in seen:
                seen.add(key)
                attacks.append({"attacker": i, "target": j, "kind": "normal", "witness": w})
        elif kinds["reverse"]:
            w = sorted(kinds["reverse"])[0]
            key = (i, j, "reverse", w)
            if key not in seen:
                seen.add(key)
                attacks.append({"attacker": i, "target": j, "kind": "reverse", "witness": w})

    return attacks


def _rank_of(x, prefs):
    """rang plus petit = plus préféré. Retourne None si inconnue."""
    return prefs.get(x, None)


def compute_attacks_sets(aba, args):
    """
    Calcule les attaques entre coalitions X,Y ⊆ A (assumptions).
    Pour chaque paire (X,Y) on regarde :
      - normal attack: il existe un argument t avec leaves(t) ⊆ X, cl(t) = overline(y) pour un y∈Y,
        et pour ce support utilisé X' = leaves(t) il n'existe pas x' ∈ X' tel que x' < y (strictement moins préféré).
      - reverse attack: il existe un argument t with leaves(t) ⊆ Y, cl(t) = overline(x) pour un x∈X,
        et il existe y' ∈ leaves(t) tel que y' < x (i.e. x est mieux que y').
    On renvoie une liste d'entrées dict:
      {"X": sorted list, "Y": sorted list, "kind": "normal"|"reverse"|"both", "witness": elem}
    """
    # index: conclusion -> list of supports (sets)
    concl2supports = {}
    for a in args:
        concl2supports.setdefault(a["conclusion"], []).append(set(a["assumptions"]))

    A = set(aba.assumptions)
    prefs = aba.preferences or {}

    # on va considérer toutes les coalitions "utiles" — ici : toutes les subsets des assumptions
    # (pour petits A, ok; si A large -> à optimiser)
    def all_subsets(s):
        lst = list(s)
        for r in range(len(lst)+1):
            from itertools import combinations
            for comb in combinations(lst, r):
                yield set(comb)

    coalitions = list(all_subsets(A))

    results = []

    # helper to pretty key
    def key_set(S):
        return tuple(sorted(S))

    # pour chaque paire X,Y
    for X in coalitions:
        for Y in coalitions:
            normal_witnesses = set()
            reverse_witnesses = set()

            # NORMAL: exists y in Y and exists support S (subset of X) s.t. cl(S) = overline(y)
            for y in Y:
                over_y = aba.contraries.get(y)
                if not over_y:
                    continue
                supports = concl2supports.get(over_y, [])
                for S in supports:
                    if not S.issubset(X):
                        continue
                    # condition normal: aucun x' in S tel que x' strictly less preferred than y
                    #  NOT exists x' with _rank_of(x') > _rank_of(y)
                    any_worse = False
                    for xp in S:
                        # xp is strictly less preferred than y <=> xp has rank > y
                        r_xp = _rank_of(xp, prefs)
                        r_y = _rank_of(y, prefs)
                        if r_xp is None or r_y is None:
                            # si non comparable, on considère qu'il n'y a pas de preuve d'infiriorité
                            continue
                        if r_xp > r_y:
                            any_worse = True
                            break
                    if not any_worse:
                        normal_witnesses.add(y)

            # REVERSE: exists x in X and exists support S' subset of Y s.t. cl(S') = overline(x)
            #            and exists y' in S' with y' strictly less preferred than x (i.e. x better than y')
            for x in X:
                over_x = aba.contraries.get(x)
                if not over_x:
                    continue
                supports = concl2supports.get(over_x, [])
                for Sprime in supports:
                    if not Sprime.issubset(Y):
                        continue
                    # condition reverse: exists y' in Sprime s.t. y' < x (y' strictly less preferred than x)
                    exist_yprime_weaker = False
                    for yp in Sprime:
                        r_yp = _rank_of(yp, prefs)
                        r_x = _rank_of(x, prefs)
                        if r_yp is None or r_x is None:
                            continue
                        if r_yp > r_x:
                            exist_yprime_weaker = True
                            break
                    if exist_yprime_weaker:
                        reverse_witnesses.add(x)

            # build result: both if both non-empty
            kind = None
            witness = None
            if normal_witnesses and reverse_witnesses:
                kind = "both"
                # choose deterministic witness (smallest by name)
                witness = sorted(list(normal_witnesses))[0]
            elif normal_witnesses:
                kind = "normal"
                witness = sorted(list(normal_witnesses))[0]
            elif reverse_witnesses:
                kind = "reverse"
                witness = sorted(list(reverse_witnesses))[0]

            if kind is not None:
                results.append({
                    "X": sorted(list(X)),
                    "Y": sorted(list(Y)),
                    "kind": kind,
                    "witness": witness
                })

    return results
