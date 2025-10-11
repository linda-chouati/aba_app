def rank_of(a, preferences):
    """
    renvoie le rang d une assumption
    -> plus le rang est petit plus l assumption est préféré
    -> si on n a pas de rang pour des aasumption par defaut on lui en met un tres grand 
    """
    if a in preferences:
        return preferences[a]
    return 10**6

def compute_attacks(aba, args, use_preferences=False):
    """
    permet de calculer les attaques entre arguments 
    """
    attacks = []
    seen = set() # pour eviter les doublons 

    # on parcour deux a deux arguments de tous les arguments 
    for A in args:
        i = A["id"]
        conclA = A["conclusion"]
        for B in args:
            j = B["id"]
            # on parcourt chaque assumption  de B 
            # le but est de voir si la conclu de A n est pas le contraire des assumption de b 
            # si c le cas alors A attaque B 
            for b in B["assumptions"]:
                if aba.contraries.get(b) == conclA:
                    if use_preferences:
                        # si au moins une assumption de A est moins pref que b
                        # on inverse l attaque : B -> A 
                        reverse = False
                        for a in A["assumptions"]:
                            if rank_of(a, aba.preferences) > rank_of(b, aba.preferences):
                                reverse = True
                                break
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
                    else:
                        # mode standard sans pref : A -> B
                        key = (i, j, "normal", b)
                        if key not in seen:
                            seen.add(key)
                            attacks.append({"attacker": i, "target": j, "kind": "normal", "witness": b})
    return attacks
