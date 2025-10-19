from copy import deepcopy

def make_non_circular(aba):
    """
    Transformation simple vers un cadre 'non-circulaire' en étageant les non-assumptions.
    Idée  : pour chaque non-assumption s, on crée s^1, s^2, ... s^(k-1)
    et on duplique les règles en décalant d'un niveau pour casser les cycles.
    (k = max(1, |L\A|))
    """
    A = set(aba.assumptions)
    L = set(aba.literals)
    R = list(aba.rules)

    non_assumps = sorted([x for x in L if x not in A])
    k = max(1, len(non_assumps))

    def head_at_level(sym, i):
        return sym if i == k else f"{sym}^{i}"

    new_L = set(L)
    new_rules = []

    for r in R:
        h = r["head"]
        body = r.get("body", [])
        body_is_atomic = all(b in A for b in body)

        if body_is_atomic:
            for i in range(1, k + 1):
                new_rules.append({"head": head_at_level(h, i), "body": list(body)})
        else:
            for i in range(2, k + 1):
                new_body = []
                for b in body:
                    if b in A:
                        new_body.append(b)
                    else:
                        bj = b if (i - 1) == k else f"{b}^{i-1}"
                        new_body.append(bj)
                new_rules.append({"head": head_at_level(h, i), "body": new_body})

    # complete L avec les symboles de niveaux
    for s in non_assumps:
        for i in range(1, k):
            new_L.add(f"{s}^{i}")

    aba.literals = new_L
    aba.rules = new_rules


def make_atomic_sensitive(aba):
    """
    Transformation 'atomic-sensistive' : on introduit pour chaque non-assumption s
    deux assumptions s_d et s_nd, avec contraires s_d ↔ s_nd et s_nd ↔ s.
    Les règles non-atomiques remplacent les non-assumptions par s_d.
    """
    A = set(aba.assumptions)
    L = set(aba.literals)
    R = list(aba.rules)

    new_A = set(A)
    new_L = set(L)
    new_rules = []
    new_contraries = deepcopy(aba.contraries)

    for s in (L - A):
        sd = f"{s}_d"
        snd = f"{s}_nd"
        new_A.update([sd, snd])
        new_L.update([sd, snd])
        new_contraries[sd] = snd
        new_contraries[snd] = s

    for r in R:
        head = r["head"]
        body = r.get("body", [])
        if all(b in A for b in body):
            new_rules.append({"head": head, "body": list(body)})
        else:
            body2 = [ (x if x in A else f"{x}_d") for x in body ]
            new_rules.append({"head": head, "body": body2})

    aba.assumptions = new_A
    aba.literals = new_L
    aba.rules = new_rules
    aba.contraries = new_contraries
