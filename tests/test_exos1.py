
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import parse_any
from src.aba_core import ABA
from src.aba_attacks import compute_attacks


def fset(xs):
    return frozenset(xs)


def test_exos1_arguments_and_attacks_match_prof():
    """
    Exo ABA (sans préférences).
    Vérifie :
      - les 8 arguments (support, conclusion) comme dans la correction
      - 10 attaques, et les paires (support->support) attendues (avec témoin)
    """
    p = ROOT / "data" / "exos1.txt"
    assert p.exists(), f"Fichier manquant: {p}"

    raw = p.read_text(encoding="utf-8")
    data, _ = parse_any({"input": raw})

    # === Construire l'ABA et les arguments
    aba = ABA.from_dict(data)
    args = aba.derive_arguments()  # <- liste de dicts: {"id","assumptions","conclusion"}

    # Ensemble attendu des arguments (support, conclusion)
    expected_args = {
        (fset(["a", "c"]), "s"),
        (fset(["a", "c"]), "t"),
        (fset(["b"]),      "b"),
        (fset([]),         "q"),
        (fset(["c"]),      "c"),
        (fset(["a"]),      "a"),
        (fset(["b", "c"]), "r"),
        (fset(["a"]),      "p"),
    }

    got_args = {(fset(a["assumptions"]), a["conclusion"]) for a in args}
    assert got_args == expected_args, (
        "Arguments différents de la correction.\n"
        f"Manquants: {sorted(expected_args - got_args)}\n"
        f"En trop:   {sorted(got_args - expected_args)}"
    )

    # === Attaques en ABA simple (sans préférences)
    atks = compute_attacks(aba, args, use_preferences=False)

    # carte id -> support (en frozenset) pour raisonner par supports
    id2sup = {a["id"]: fset(a["assumptions"]) for a in args}

    # arêtes observées (supportX, supportY, kind, witness)
    got_edges = {
        (id2sup[t["attacker"]], id2sup[t["target"]], t["kind"], t.get("witness"))
        for t in atks
    }

    #  donne 10 attaques : on vérifie d'abord le compte brut
    assert len(atks) == 10, f"Nombre d'attaques: attendu 10, obtenu {len(atks)}"

    # Puis que chaque attendue est bien présente au moins une fois.
    expected_edges = {
        # s (support {a,c}) contre tout argument qui utilise b
        (fset(["a", "c"]), fset(["b"]),      "normal", "b"),
        (fset(["a", "c"]), fset(["b", "c"]), "normal", "b"),

        # t (support {a,c}) contre tout argument qui utilise c
        (fset(["a", "c"]), fset(["c"]),      "normal", "c"),
        (fset(["a", "c"]), fset(["a", "c"]), "normal", "c"),
        (fset(["a", "c"]), fset(["b", "c"]), "normal", "c"),

        # r (support {b,c}) contre tout argument qui utilise a
        (fset(["b", "c"]), fset(["a"]),      "normal", "a"),
        (fset(["b", "c"]), fset(["a", "c"]), "normal", "a"),
    }

    assert expected_edges.issubset(got_edges), (
        "Certaines arêtes attendues manquent (par supports).\n"
        f"Manquantes: {sorted(expected_edges - got_edges)}"
    )
