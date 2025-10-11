# src/aba_transform.py
from copy import deepcopy

def has_cycles(literals, rules, assumptions):
    graph = {l: [] for l in literals}
    for r in rules:
        h = r["head"]
        for x in r.get("body", []):
            graph.setdefault(x, []).append(h)

    seen = set()
    stack = set()

    def dfs(u):
        if u in stack:
            return True
        if u in seen:
            return False
        seen.add(u)
        stack.add(u)
        for v in graph.get(u, []):
            if dfs(v):
                return True
        stack.remove(u)
        return False

    for l in literals:
        if l not in seen and dfs(l):
            return True
    return False


def make_non_circular(aba):
    A = set(aba.assumptions)
    L = set(aba.literals)
    R = list(aba.rules)

    # k = |L\A|
    non_assumps = sorted([s for s in L if s not in A])
    k = max(1, len(non_assumps))

    new_L = set(L)
    new_rules = []

    def head_at_level(s, i):
        # Au niveau k, on renomme s^k en s (cf. cours)
        return s if i == k else f"{s}^{i}"

    for r in R:
        s = r["head"]
        body = r.get("body", [])

        is_atomic = all(b in A for b in body)

        if is_atomic:
            # i = 1..k
            for i in range(1, k + 1):
                hi = head_at_level(s, i)
                bi = list(body)  # inchangé
                new_rules.append({"head": hi, "body": bi})
        else:
            # i = 2..k  (pas de niveau 1)
            for i in range(2, k + 1):
                hi = head_at_level(s, i)
                bi = []
                for b in body:
                    if b in A:
                        bi.append(b)
                    else:
                        # pour i, on prend b^{i-1}; au niveau 2 => b^1
                        bj = b if (i - 1) == k else f"{b}^{i-1}"
                        # remarque: à i-1 == k on retomberait sur b (puisque niveau k == s)
                        # mais comme i<=k, i-1 <= k-1, donc on reste en b^{i-1}.
                        bi.append(bj)
                new_rules.append({"head": hi, "body": bi})

    # étend L avec s^i pour i = 1..k-1 (pas pour k)
    for s in non_assumps:
        for i in range(1, k):
            new_L.add(f"{s}^{i}")

    aba.literals = new_L
    aba.rules = new_rules



def make_atomic_sensitive(aba):
    A = set(aba.assumptions)
    L = set(aba.literals)
    R = list(aba.rules)

    new_A = set(A)
    new_L = set(L)
    new_rules = []
    new_contraries = deepcopy(aba.contraries)

    # on introduit, pour chaque non-assumption s, deux nouvelles assumptions s_d et s_nd
    for s in (L - A):
        sd = f"{s}_d"
        snd = f"{s}_nd"
        new_A.update([sd, snd])
        new_L.update([sd, snd])
        new_contraries[sd] = snd   # overline(sd) = snd
        new_contraries[snd] = s    # overline(snd) = s

    # transformation des règles
    for r in R:
        head = r["head"]
        body = r.get("body", [])
        if all(b in A for b in body):
            # corps purement assumptif : règle inchangée
            new_rules.append({"head": head, "body": list(body)})
        else:
            # remplace chaque non-assumption s du corps par s_d
            body2 = [ (x if x in A else f"{x}_d") for x in body ]
            new_rules.append({"head": head, "body": body2})

    aba.assumptions = new_A
    aba.literals = new_L
    aba.rules = new_rules
    aba.contraries = new_contraries
