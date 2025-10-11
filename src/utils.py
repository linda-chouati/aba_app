def parse_preferences(text):
    parts = str(text).split(">")
    levels = []
    for p in parts:
        p = p.strip()
        if p:
            items = [x.strip() for x in p.split(",") if x.strip()]
            levels.append(items)
    pref = {}
    level = 0
    for items in levels:
        for it in items:
            pref[it] = level
        level += 1
    return pref
