
import json
import os
from src.aba_core import ABA
from src.aba_transform import make_non_circular, make_atomic_sensitive
from src.aba_attacks import compute_attacks

def run_file(path_in="data/exemple.json",
             do_non_circular=True,
             do_atomic=False,
             use_preferences=False,
             save_result=True,
             path_out="outputs/result.json"):
    with open(path_in, "r", encoding="utf-8") as f:
        data = json.load(f)

    aba = ABA()
    aba.parse_from_json(data)
    aba.validate()

    if do_non_circular:
        make_non_circular(aba)
    if do_atomic:
        make_atomic_sensitive(aba)

    args = aba.derive_arguments()
    atks = compute_attacks(aba, args, use_preferences=use_preferences)

    print("\n=== Arguments ===")
    for a in args:
        print(f"A{a['id']}: {a['conclusion']} <= {sorted(list(a['assumptions']))}")

    print("\n=== Attaques ===")
    for t in atks:
        print(f"{t['kind']}: A{t['attacker']} -> A{t['target']}  (cible '{t['witness']}')")

    if save_result:
        os.makedirs(os.path.dirname(path_out), exist_ok=True)
        with open(path_out, "w", encoding="utf-8") as f:
            json.dump(aba.export_results(args, atks), f, ensure_ascii=False, indent=2)
        print(f"\nRésultat enregistré dans : {path_out}")



if __name__ == "__main__":
    run_file(
        path_in="data/exemple.json",
        do_non_circular=False,     
        do_atomic=False,         
        use_preferences=False ,   
        save_result=True,
        path_out="outputs/result.json"
    )
